import docx
doc = docx.Document()
p = doc.add_paragraph("This is a test document.")
doc.add_comment(p.runs, text="This is a test comment", author="Test")
doc.save("test_comment.docx")
