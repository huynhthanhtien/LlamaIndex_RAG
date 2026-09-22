from llama_index.core import Document, SummaryIndex

doc = Document(text = "Điều 15. Sinh viên nghỉ học quá 20% số tiết sẽ không đủ điều kiện dự thi.")
print("Document tạo thành công!")
print("Nội dung:", doc.text)
print("ID tự sinh:", doc.doc_id)

index = SummaryIndex.from_documents([doc])
print("\nIndex build thành công!")
print("Số Document trong Index:", len(index.docstore.docs))