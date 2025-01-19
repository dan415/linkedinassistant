import logging

from chromadb.utils.embedding_functions import create_langchain_embedding
from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from typing import TypedDict, List, Optional
from typing_extensions import Required, NotRequired
from src.core.llm.retrieval.rag import DocumentInformationRetrieval
from src.core.llm.provider import LLMProvider
from src.core.utils.logging import ServiceLogger


class ProcessingState(TypedDict, total=False):
    # Define the structure of the state that flows through the workflow.
    text: Required[str]  # Input text to be processed
    chunks: NotRequired[List[str]]  # List of text chunks after splitting
    documents: NotRequired[List[Document]]  # List of documents created from chunks
    summary: NotRequired[str]  # Summary of the documents
    terms_or_questions_list: NotRequired[List[str]]  # List of terms or questions generated
    vectorstore: NotRequired[Optional[Chroma]]  # Vectorstore for similarity search
    relevant_chunks: NotRequired[List[str]]  # List of relevant chunks retrieved
    answers: NotRequired[List[str]]  # List of answers generated for questions
    formatted_dialog: NotRequired[str]  # Formatted Q&A dialog
    title: NotRequired[str]  # Extracted title of the document


class RetrieverWorkflow:
    """Encapsulates the workflow setup and execution for a retriever."""

    def __init__(self, chunk_size,
                 chunk_overlap,
                 model_provider,
                 embeddings_provider,
                 n_chunk_results,
                 query_expansion_prompt,
                 answer_prompt,
                 title_extraction_prompt,
                 has_title=False,
                 logger: logging.Logger = ServiceLogger(__name__)
                 ):
        # Initialize parameters for chunking, LLM provider, embeddings, and result limits.
        self.logger = logger
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.llm = LLMProvider.build(model_provider)
        self.embedding_model = LLMProvider.build(embeddings_provider)
        self.n_chunk_results = n_chunk_results
        self.has_title = has_title
        self.query_expansion_prompt = query_expansion_prompt
        self.answer_prompt = answer_prompt
        self.title_extraction_prompt = title_extraction_prompt

    def create_documents(self, state: ProcessingState):
        """
        Convert text chunks into document objects with metadata.
        Process:
            - Iterates over the list of chunks.
            - Creates Document objects for each chunk with metadata specifying the chunk order.

        :param: state (ProcessingState): The current processing state containing the text chunks to convert.

        :returns: ProcessingState: Updated state with the documents stored in the 'documents' field.
        """
        self.logger.info("Creating documents from chunks.")
        try:
            state['documents'] = [
                Document(page_content=chunk, metadata={'chunk_order': idx})
                for idx, chunk in enumerate(state['chunks'])
            ]
            self.logger.info(f"Created {len(state['documents'])} documents.")
        except Exception as e:
            self.logger.error(f"Error creating documents: {e}")
            raise
        return state

    def format_dialog(self, state: ProcessingState):
        """
        Format the list of questions and answers into a readable dialog structure.

        :param: state (ProcessingState): The current processing state containing the questions and their corresponding
             answers.

        :returns: ProcessingState: Updated state with the formatted dialog stored in the 'formatted_dialog' field.
        """
        self.logger.info("Formatting Q&A dialog.")
        try:
            state['formatted_dialog'] = "\n\n".join(
                f"Q: {q}\nA: {a}"
                for q, a in zip(state['terms_or_questions_list'], state['answers'])
            )
            self.logger.info("Dialog formatting completed.")
        except Exception as e:
            self.logger.error(f"Error formatting dialog: {e}")
            raise
        return state

    def setup_workflow(self):
        # Set up the workflow graph by defining nodes and their connections.
        self.logger.debug("Setting up workflow.")
        workflow = StateGraph(ProcessingState)

        # Add nodes for processing stages.
        workflow.add_node("split_text", self.split_text)
        workflow.add_node("create_documents", self.create_documents)
        workflow.add_node("summarize_documents", self.summarize_documents)
        workflow.add_node("generate_terms", self.generate_terms)
        workflow.add_node("create_vectorstore", self.create_vectorstore)
        workflow.add_node("retrieve_relevant_chunks", self.retrieve_relevant_chunks)
        workflow.add_node("answer_questions", self.answer_questions)
        workflow.add_node("format_dialog", self.format_dialog)

        if not self.has_title:
            workflow.add_node("extract_title", self.extract_title)

        # Define edges for workflow execution.
        workflow.add_edge(START, "split_text")
        workflow.add_edge("split_text", "create_documents")
        workflow.add_edge("create_documents", "summarize_documents")
        workflow.add_edge("summarize_documents", "generate_terms")
        workflow.add_edge("generate_terms", "create_vectorstore")
        workflow.add_edge("create_vectorstore", "retrieve_relevant_chunks")
        workflow.add_edge("retrieve_relevant_chunks", "answer_questions")
        workflow.add_edge("answer_questions", "format_dialog")

        if not self.has_title:
            workflow.add_edge("format_dialog", "extract_title")
            workflow.add_edge("extract_title", END)
        else:
            workflow.add_edge("format_dialog", END)
        self.logger.debug("Workflow setup complete.")
        return workflow

    def split_text(self, state: ProcessingState):
        """
        Split the input text into manageable chunks for processing.
        Process:
            - Uses the RecursiveCharacterTextSplitter to divide the text into chunks of a defined size.
            - Adds overlap between chunks as per the configuration.

        :param: state (ProcessingState): The current processing state containing the input text to be split.

        :returns: ProcessingState: Updated state with the split chunks stored in the 'chunks' field.
        """
        self.logger.info("Splitting text into chunks.")
        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
            )
            state['chunks'] = splitter.split_text(state['text'])
            self.logger.info(f"Text split into {len(state['chunks'])} chunks.")
        except Exception as e:
            self.logger.error(f"Error splitting text: {e}")
            raise
        return state

    def summarize_documents(self, state: ProcessingState):
        """
        Generate a summary of the input documents using a language model.
        Process:
            - Splits the list of documents into manageable chunks based on the configured chunk size.
            - Invokes the language model chain to process each chunk and generate partial summaries.
            - Concatenates partial summaries into a single cohesive summary.

        :param: state (ProcessingState): The current processing state containing the list of documents to summarize.

        :returns: ProcessingState: Updated state with the generated summary stored in the 'summary' field.
        """
        self.logger.info("Summarizing documents.")
        try:
            chain = load_summarize_chain(self.llm, chain_type="stuff")
            summaries = [
                chain.invoke(state['documents'][i:i + self.chunk_size])
                for i in range(0, len(state['documents']), self.chunk_size)
            ]
            state['summary'] = "\n".join(s.get("output_text", "") for s in summaries)
            self.logger.info("Summarization completed.")
        except Exception as e:
            self.logger.error(f"Error summarizing documents: {e}")
            raise
        return state

    def generate_terms(self, state: ProcessingState):
        """
        Create a list of terms or questions based on the document summary.
        Process:
            - Uses a language model to generate terms or questions from the summary.
            - Splits the generated output into a list of strings.

        :param: state (ProcessingState): The current processing state containing the document summary.

        :returns: ProcessingState: Updated state with the list of generated terms or questions stored in the
             'terms_or_questions_list' field.
        """
        self.logger.info("Generating terms or questions from summary.")
        try:
            chain = PromptTemplate(
                input_variables=["summary"], template=self.query_expansion_prompt
            ) | self.llm | StrOutputParser()

            state['terms_or_questions_list'] = chain.invoke({"summary": state['summary']}).strip().split("\n")
            self.logger.info(f"Generated terms/questions: {state['terms_or_questions_list']}")
        except Exception as e:
            self.logger.error(f"Error generating terms: {e}")
            raise
        return state

    def create_vectorstore(self, state: ProcessingState):
        """
        Build a vector store for efficient similarity searches.
        Process:
            - Extracts the text content and metadata from the documents in the state.
            - Uses the configured embeddings provider to compute embeddings for the document texts.
            - Creates a Chroma vector store to enable fast similarity searches.

        :param: state (ProcessingState): The current processing state containing the documents to be converted
            into a vector store.

        :returns: ProcessingState: Updated state with the vector store stored in the 'vectorstore' field.
        """
        self.logger.info("Creating vector store from documents.")
        try:
            state['vectorstore'] = Chroma.from_texts(
                [doc.page_content for doc in state['documents']],
                embedding=self.embedding_model,
                metadatas=[doc.metadata for doc in state['documents']],
                collection_name="retrieval_state",
                persist_directory=None
            )
            self.logger.info("Vectorstore created.")
        except Exception as e:
            self.logger.error(f"Error creating vectorstore: {e}")
            raise
        return state

    def retrieve_relevant_chunks(self, state: ProcessingState):
        """
        Retrieve relevant chunks of text using similarity search in the vector store.
        Process:
            - The method iterates through the terms or questions provided in the state.
            - It uses the vector store to perform a similarity search for each term or question.
            - The results are de-duplicated while preserving their order.

        :param: state (ProcessingState): The current processing state containing the vector store and query terms
            or questions.

        :returns: ProcessingState: Updated state with a list of relevant chunks stored in the 'relevant_chunks' field.
        """
        self.logger.info("Retrieving relevant chunks from vectorstore.")
        try:
            results = [
                chunk
                for term in state['terms_or_questions_list']
                for chunk in state['vectorstore'].similarity_search(term, k=self.n_chunk_results)
            ]
            # We sort the retrieved documents to facilitate understanding
            results.sort(key=lambda page: page.metadata["chunk_order"])
            # We removed duplicated returned chunks
            results = {page.metadata["chunk_order"]: page for page in results}
            # Take just the strings
            state['relevant_chunks'] = [page.page_content for page in
                                        results.values()]  # Preserve order while ensuring uniqueness.
            self.logger.info(f"Retrieved {len(state['relevant_chunks'])} relevant chunks.")
        except Exception as e:
            self.logger.error(f"Error retrieving relevant chunks: {e}")
            raise
        return state

    def answer_questions(self, state: ProcessingState):
        """
        Generate answers to a list of questions using the retrieved relevant chunks.
        Process:
            - The method takes the list of relevant chunks and questions from the state.
            - It uses a language model to provide an answer for each question based on the provided context.
            - The generated answers are stored in the state for further use.

        :param: state (ProcessingState): The current processing state containing questions and relevant chunks.

        :returns: ProcessingState: Updated state with answers generated for each question,
        stored in the 'answers' field.
        """
        self.logger.info("Answering questions.")
        try:
            chain = PromptTemplate(
                input_variables=["context", "question"],
                template=self.answer_prompt
            ) | self.llm | StrOutputParser()

            state['answers'] = [
                chain.invoke({"context": "\n".join(state['relevant_chunks']), "question": question})
                for question in state['terms_or_questions_list']
            ]
            self.logger.info("Questions answered.")
        except Exception as e:
            self.logger.error(f"Error answering questions: {e}")
            raise
        return state

    def extract_title(self, state: ProcessingState):
        """
        Extract the title of a document using a language model.

        :param: state (ProcessingState): The current state containing the text to extract the title from.

        :returns: ProcessingState: Updated state with the extracted title stored in the 'title' field.
        """
        self.logger.info("Extracting document title.")
        try:
            chain = PromptTemplate(
                input_variables=["text"], template=self.title_extraction_prompt
            ) | self.llm | StrOutputParser()

            state['title'] = chain.invoke({"text": state['text'][:min(len(state['text']), 2000)]}).strip()
            self.logger.info(f"Extracted title: {state['title']}")
        except Exception as e:
            self.logger.error(f"Error extracting title: {e}")
            raise
        return state


class LangChainRetriever(DocumentInformationRetrieval):
    """Main class orchestrating retrieval workflows."""
    _CONFIG_SCHEMA = "llm-retrieval-langchain"

    def __init__(self, document_name="", logger: logging.Logger = ServiceLogger(__name__)):
        # Initialize the retriever with the document name and other properties.
        super().__init__(document_name, logger=logger)
        self.logger.debug(f"Initializing LangChainRetriever with document_name: {document_name}")
        self.chunk_size = None
        self.chunk_overlap = None
        self.model_provider = None
        self.embeddings_provider = None
        self.query_expansion_prompt = None
        self.answer_prompt = None
        self.title_extraction_prompt = None
        self.n_chunk_results = None
        self.workflow_manager = None
        self.workflow = None

    def __enter__(self):
        """
        Load configuration and initialize the workflow manager.
        """
        self.load_config()
        self.workflow_manager = RetrieverWorkflow(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            model_provider=self.model_provider,
            embeddings_provider=self.embeddings_provider,
            n_chunk_results=self.n_chunk_results,
            answer_prompt=self.answer_prompt,
            query_expansion_prompt=self.query_expansion_prompt,
            title_extraction_prompt=self.title_extraction_prompt,
            has_title=self.document_name != ""
        )
        self.workflow = self.workflow_manager.setup_workflow()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up resources when exiting the context.
        """
        self.workflow_manager = None
        self.workflow = None

    def search(self, paragraphs, queries=None):
        """
        Execute the retrieval workflow to process input text and dynamically generate questions and answers.

        :param: paragraphs (List[str]): A list of paragraphs that constitute the input text.
            queries (Optional[List[str]]): Ignored. This retriever dynamically generates its own queries.

        :returns: Tuple[str, str]: A formatted Q&A dialog string and the extracted title of the document.
        """
        self.logger.info("Starting search process.")
        if queries:
            self.logger.warning("This retriever dynamically generates queries; input queries are ignored.")

        initial_state = {"text": " ".join(paragraphs)}
        result = self.workflow.compile().invoke(initial_state)
        return result.get("formatted_dialog", "No dialog generated"), result.get("title", "Untitled Document")
