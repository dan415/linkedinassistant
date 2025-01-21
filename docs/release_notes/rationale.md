# Release Notes

## v2.0.0

Welcome to **v2.0.0**—a transformative update that redefines the capabilities of the LinkedIn Gen AI Posting Creator Assistant. This major release introduces groundbreaking features, elevates functionality, and delivers seamless integration with modern cloud services. Here’s what’s new:

### What's changed

- **External Configuration Management**: All state configurations are now hosted externally, significantly boosting maintainability and portability.
  - **MongoDB Atlas**: Manages configurations, conversation histories, and publications (free up to 25GB).
  - **Backblaze B2**: Cloud storage for PDF files and images (free up to 10GB).
  - **HashiCorp Vault**: Secure storage for secrets and credentials used (free for static secrets). Hashicorp vault credentials are now stored in the system's keyring.
- **New available source**: 
  - From YouTube urls: Simply pass YouTube URLs to the bot. The bot will extract transcripts, metadata, and thumbnails to craft compelling LinkedIn posts.
- **Improved PDF text extraction**:
  - **Docling**: Enhanced PDF text extraction for more accurate and insightful post generation.
  - **PyMuPDF**: Added as lightweight PDF extraction alternative.
- **Extended LLM support**:
  - **Google Gen AI Studio Integration**: Access to Google Gen AI Studio models, including latest Flash 2 model.
  - **Groq**: Integration with all Groq models
  - **Deepseek**: Integration with Deepseek models, including the latest Deepseek V3 model.
  - **Custom models**: Easily add custom models to the bot if compatible with the OpenAI API
- **Enhanced Post Generation**:
  - **AI-Generated Art**: Create custom visuals using DALL-E 3’s powerful AI image generation.
  - **Image Integration for Posts**: Use YouTube video thumbnails, embedded source images, or manually uploaded images as post visuals.
- **Improved Retrieval Pipeline**:
  - **LangChain RAG workflow**: Replaces the legacy ColBERT-based retrieval system, offering advanced vector search capabilities.
- **New Bot Commands**
  - **Manual Uploads**: Send PDF documents directly to the bot to add them to the queue
  - **Image Management**: Upload, list, and remove images for posts
  - **YouTube Integration**: Add YouTube URLs to the bot for post creation
  - **Search Engine Activation**: Enable or disable the search engine for post generation
- **Agent Boosted Capabilities**
  - **Tool Usage**: Access to all pre-built LangChain tools for enhanced post creation, like accessing the internet, generate images, search with brave or acccess arxiv papers.
  - **Persistent Conversation History**: Maintain conversation history while the post is not yet posted by integrating automatic checkpointing of conversation messages on MongoDB with custom made memory saver.
- **Easier installation**:
  - Only need to set up external services and vault secrets prior to installation.
  - **Insallation scripts**: Added installation scripts for easy setup and configuration for both Linux and Windows


- **Improved Logging**: Enhanced logging for better debugging and monitoring.
