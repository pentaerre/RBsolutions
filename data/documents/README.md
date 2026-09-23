Drop PDF, XLSX, PPTX, DOCX, or CSV files here (this folder or inbox/).

Atrium's Watchman sees new files. Mailroom can also download email
attachments into inbox/ when IMAP is configured.

The pipeline then:
  1. Parser reads the file
  2. Triage classifies it (invoice, policy, spreadsheet, ...)
  3. Chunker sends text to RAG (Qdrant + Neo4j)
  4. Extractor writes structured rows to Postgres when it is an invoice/sheet
  5. Clerk files the original under classified/{type}/

The included `welcome.pdf` is a tiny starter document so you can try chat
before adding your own files.
