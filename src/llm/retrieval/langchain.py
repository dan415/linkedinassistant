import os
from dotenv import load_dotenv
from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from typing import TypedDict, List, Optional
from typing_extensions import Required, NotRequired
from src.llm.retrieval.rag import DocumentInformationRetrieval
import src.core.utils.functions as F
from src.llm.provider import LLMProvider

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class ProcessingState(TypedDict, total=False):
    text: Required[str]
    chunks: NotRequired[List[str]]
    documents: NotRequired[List[Document]]
    summary: NotRequired[str]
    terms_or_questions_list: NotRequired[List[str]]
    vectorstore: NotRequired[Optional[Chroma]]
    relevant_chunks: NotRequired[set[str]]
    answers: NotRequired[List[str]]
    formatted_dialog: NotRequired[str]
    title: NotRequired[str]


class LangChainRetriever(DocumentInformationRetrieval):
    def __init__(self, document_name):
        self.embeddings_provider = ""
        self.model_provider = ""
        self.chunk_size = 1000
        self.chunk_overlap = 100
        self.query_expansion_prompt = ""
        self.answer_prompt = ""
        self.title_extraction_prompt = ""
        self.combine_chunks_prompt = ""
        super().__init__(document_name)

    def __enter__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size,
                                                            chunk_overlap=self.chunk_overlap)
        self.embeddings = LLMProvider.build(self.embeddings_provider)
        self.llm = LLMProvider.build(self.model_provider)
        self.workflow = StateGraph(ProcessingState)

        self.terms_prompt = PromptTemplate(
            input_variables=["summary"],
            template=self.query_expansion_prompt
        )

        self.answer_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=self.answer_prompt
        )

        self.title_prompt = PromptTemplate(
            input_variables=["text"],
            template=self.title_extraction_prompt
        )

        self.terms_chain = self.terms_prompt | self.llm | StrOutputParser()
        self.answer_chain = self.answer_prompt | self.llm | StrOutputParser()
        self.title_chain = self.title_prompt | self.llm | StrOutputParser()

        self.workflow.add_node("split_text", self.split_text)
        self.workflow.add_node("create_documents", self.create_documents)
        self.workflow.add_node("summarize_documents", self.summarize_documents)
        self.workflow.add_node("generate_terms", self.generate_terms)
        self.workflow.add_node("create_vectorstore", self.create_vectorstore)
        self.workflow.add_node("retrieve_relevant_chunks", self.retrieve_relevant_chunks)
        self.workflow.add_node("answer_questions", self.answer_questions)
        self.workflow.add_node("format_dialog", self.format_dialog)
        self.workflow.add_node("extract_title", self.extract_title)

        self.workflow.add_edge(START, "split_text")
        self.workflow.add_edge("split_text", "create_documents")
        self.workflow.add_edge("create_documents", "summarize_documents")
        self.workflow.add_edge("summarize_documents", "generate_terms")
        self.workflow.add_edge("generate_terms", "create_vectorstore")
        self.workflow.add_edge("create_vectorstore", "retrieve_relevant_chunks")
        self.workflow.add_edge("retrieve_relevant_chunks", "answer_questions")
        self.workflow.add_edge("answer_questions", "format_dialog")
        self.workflow.add_edge("format_dialog", "extract_title")
        self.workflow.add_edge("extract_title", END)
        self.retriever = self.workflow.compile()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self

    @property
    def config_schema(self):
        return "llm-retrieval-langchain"

    def split_text(self, state: ProcessingState):
        logger.info("Splitting text into chunks.")
        if not state.get('text'):
            raise ValueError("No text provided in state")
        try:
            state['chunks'] = self.text_splitter.split_text(state['text'])
            logger.info(f"Text split into {len(state['chunks'])} chunks.")
            return state
        except Exception as e:
            logger.error(f"Error splitting text: {str(e)}")
            raise Exception(f"Error splitting text: {str(e)}")

    def create_documents(self, state: ProcessingState):
        logger.info("Creating documents from chunks.")
        try:
            documents = []
            for idx, chunk in enumerate(state['chunks']):
                doc = Document(page_content=chunk, metadata={'chunk_order': idx})
                documents.append(doc)
            state['documents'] = documents
            logger.info(f"Created {len(state['documents'])} documents with order metadata.")
        except Exception as e:
            logger.error(f"Error creating documents: {e}")
            state['documents'] = []
        return state

    def summarize_documents(self, state: ProcessingState):
        logger.info("Summarizing documents.")
        try:
            # First, create smaller groups of documents to summarize
            docs = state['documents']
            chunk_size = 4  # Number of documents to summarize at once
            summaries = []

            # First level of summarization - summarize documents in small groups
            for i in range(0, len(docs), chunk_size):
                chunk = docs[i:i + chunk_size]
                chain = load_summarize_chain(self.llm, chain_type="stuff")
                chunk_summary = chain.invoke(chunk)
                # Extract the actual summary text from the chain output
                if isinstance(chunk_summary, dict):
                    chunk_summary = chunk_summary.get('output_text', '')
                summaries.append(Document(page_content=chunk_summary))

            # If we still have too many summaries, summarize them again
            if len(summaries) > chunk_size:
                chain = load_summarize_chain(self.llm, chain_type="stuff")
                final_summary = chain.invoke(summaries)
                if isinstance(final_summary, dict):
                    final_summary = final_summary.get('output_text', '')
            else:
                chain = load_summarize_chain(self.llm, chain_type="stuff")
                final_summary = chain.invoke(summaries)
                if isinstance(final_summary, dict):
                    final_summary = final_summary.get('output_text', '')

            state['summary'] = final_summary
            logger.info("Summarization completed.")
            logger.info(f"Final summary length: {len(final_summary)}")
        except Exception as e:
            logger.error(f"Error in summarization: {e}")
            state['summary'] = "Error occurred during summarization"
        return state

    def generate_terms(self, state: ProcessingState):
        logger.info("Generating terms or questions from summary.")
        try:
            # Ensure the summary is not too long for the model
            summary = state['summary']
            max_tokens = 3000  # Leave room for the prompt and completion

            # If summary is too long, take the first part that fits
            if len(summary) > max_tokens:
                summary = summary[:max_tokens] + "..."

            terms_or_questions = self.terms_chain.invoke({"summary": summary})
            state['terms_or_questions_list'] = terms_or_questions.strip().split("\n")
            logger.info(f"Generated terms/questions: {state['terms_or_questions_list']}")
        except Exception as e:
            logger.error(f"Error generating terms: {e}")
            state['terms_or_questions_list'] = ["Error occurred during term generation"]
        return state

    def create_vectorstore(self, state: ProcessingState):
        logger.info("Creating vector store from documents.")
        try:
            if 'vectorstore' in state:
                logger.info("Vectorstore already exists. Skipping creation.")
                return state  # Avoid recreating if it exists
            pages = state.get('documents', [])  # Reuse existing documents if available
            if not pages:
                pages = self.text_splitter.create_documents(self.text_splitter.split_text(state['text']))
            pages_str = [page.page_content for page in pages]
            metadatas = [{'chunk_order': page.metadata.get('chunk_order', -1)} for page in pages]
            state['vectorstore'] = Chroma.from_texts(
                pages_str,
                self.embeddings,
                metadatas=metadatas,
                collection_name="processing_state",
                persist_directory=None
            )
            logger.info("Vector store created with chunk order metadata.")
        except Exception as e:
            logger.error(f"Error creating vectorstore: {e}")
            state['vectorstore'] = None
        return state

    def retrieve_relevant_chunks(self, state: ProcessingState):
        logger.info("Retrieving relevant chunks from vector store.")
        try:
            relevant_chunks = []
            for term in state['terms_or_questions_list']:
                similar_docs = state['vectorstore'].similarity_search(term, k=5)
                similar_docs = [doc.page_content for doc in similar_docs]
                relevant_chunks.extend(similar_docs)
            logger.info(f"Length before as set: {len(relevant_chunks)}")
            relevant_chunks = set(relevant_chunks)
            logger.info(f"Length after as set: {len(relevant_chunks)}")
            state['relevant_chunks'] = relevant_chunks
            logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks.")
            to_str = '\n'.join(state['relevant_chunks'])
            logger.info(f"{to_str}")
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            state['relevant_chunks'] = set()
        return state

    def answer_questions(self, state: ProcessingState):
        logger.info("Generating answers for each question using relevant chunks.")
        try:
            answers = []
            relevant_chunks = list(state['relevant_chunks'])

            # For each question
            for question in state['terms_or_questions_list']:
                logger.info(f"Processing question: {question}")

                # Step 1: Get individual answers from each chunk (Map phase)
                chunk_size = 2000  # Approximate size in characters for each chunk
                chunk_answers = []

                for i in range(0, len(relevant_chunks), 3):  # Process 3 chunks at a time
                    chunk_group = relevant_chunks[i:i + 3]
                    context = "\n".join(chunk_group)

                    # Get answer for this chunk group
                    try:
                        answer = self.answer_chain.invoke({
                            "context": context,
                            "question": question
                        })
                        if answer.strip():  # Only include non-empty answers
                            chunk_answers.append(answer.strip())
                    except Exception as e:
                        logger.error(f"Error processing chunk group: {e}")

                # Step 2: Combine answers (Reduce phase)
                if chunk_answers:
                    combine_prompt = PromptTemplate(
                        template=self.combine_chunks_prompt,
                        input_variables=["question", "answers"]
                    )

                    combine_chain = combine_prompt | self.llm | StrOutputParser()

                    try:
                        final_answer = combine_chain.invoke({
                            "question": question,
                            "answers": "\n\n".join(chunk_answers)
                        })
                    except Exception as e:
                        logger.error(f"Error combining answers: {e}")
                        final_answer = chunk_answers[0]  # Fall back to first answer if combination fails
                else:
                    final_answer = "Based on the available context, I cannot provide a complete answer to this question."

                answers.append(final_answer.strip())
                logger.info(f"Generated answer for question: {question[:100]}...")

            state['answers'] = answers
            logger.info(f"Generated {len(answers)} answers.")
        except Exception as e:
            logger.error(f"Error generating answers: {e}")
            state['answers'] = []
        return state

    def format_dialog(self, state: ProcessingState):
        logger.info("Formatting Q&A as dialog.")
        try:
            formatted_parts = []

            for q, a in zip(state['terms_or_questions_list'], state['answers']):
                # Add two newlines before each Q&A pair except the first one
                if formatted_parts:
                    formatted_parts.append("")

                # Format question and answer with proper indentation
                formatted_parts.extend([
                    f"Q: {q.strip()}",
                    f"A: {a.strip()}"
                ])

            # Join all parts with newlines
            state['formatted_dialog'] = "\n".join(formatted_parts)
            logger.info("Dialog formatting completed.")

        except Exception as e:
            logger.error(f"Error formatting dialog: {e}")
            state['formatted_dialog'] = "Error occurred during dialog formatting"
        return state

    def extract_title(self, state: ProcessingState):
        """Extract title from the document text using LLM.
        
        :param state: The document text to extract title from
        :return: Extracted title as string
        """
        logger.info("Extracting title from document text")
        try:
            # Take first 2000 characters as context for title extraction
            context = state['text'][:2000]
            title = self.title_chain.invoke({"text": context})
            state['title'] = title.strip()
            logger.info(f"Title extracted: {title}")
        except Exception as e:
            logger.error(f"Error extracting title: {e}")
            state['title'] = "Untitled Document"
        return state

    def search(self, paragraphs, queries=None):
        if queries:
            logger.warning("This type of retriever does not accept queries as it creates them dinamically. Ignoring "
                           "passed queries")

        initial_state = {'text': " ".join(paragraphs)}
        result = self.retriever.invoke(initial_state)
        return result.get('formatted_dialog', 'No dialog generated'), result.get('title', 'Untitled Document')


def process_pdf(pdf_path):
    logger.info(f"Processing PDF: {pdf_path}")
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        import PyPDF2
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            wholetext = []
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                wholetext.append(page.extract_text())

        with LangChainRetriever("pdf") as retriever:
            return retriever.search(wholetext)

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return None


if __name__ == "__main__":
    load_dotenv()
    pdf_path = r"/res/manual_pdfs/2311.01017v1.pdf"
    final_article, title = process_pdf(pdf_path)
    if final_article:
        logger.info("Final article generated successfully.")
        print(f"Title: {title}")
        print(final_article)
    else:
        logger.error("Failed to generate article")
        print("Failed to generate article")
