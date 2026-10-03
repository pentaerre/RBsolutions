Drop PDF, XLSX, PPTX, DOCX, or CSV files here (this folder or inbox/).

Atrium's Watchman sees new files. Mailroom can also download email
attachments into inbox/ when IMAP is configured.

The pipeline then:
  1. Watchman registers the arrival
  2. Reader extracts the first pages
  3. Taxonomist labels class / subclass (does not move the file)
  4. Clerk creates classified/{class}/{subclass} and moves the original there

The IDP line (Parser → Triage → Extractor) is a separate utility. Clerk
also files those leftovers under classified/{type}/.

The included `welcome.pdf` is a tiny starter document so you can try chat
before adding your own files.
