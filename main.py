import os
import gradio as gr
from markitdown import MarkItDown
import time
from pymongo import MongoClient

# Cấu hình MongoDB (chỉ khi cần)
USE_MONGO = True  # Thay đổi giá trị này để bật/tắt MongoDB

# Nếu sử dụng MongoDB, cấu hình kết nối MongoDB
if USE_MONGO:
    mongo_uri = "mongodb://admin:password@localhost:27017/"  # Sử dụng tên dịch vụ Docker làm hostname
    client = MongoClient(mongo_uri)
    db = client["file_processing"]
    collection = db["processing_status"]

# Hàm chuyển đổi file sang Markdown
def convert_file_to_markdown(file_path):
    try:
        # Kiểm tra xem file có tồn tại không
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Error: File {file_path} does not exist")

        # Sử dụng MarkItDown để chuyển đổi file sang Markdown
        md = MarkItDown(enable_plugins=False)
        result = md.convert(file_path)

        # Tạo tên file mới với đuôi .md
        new_filename = os.path.basename(file_path).rsplit(".", 1)[0] + ".md"
        new_file_path = os.path.join("processed_files", new_filename)

        # Đảm bảo thư mục processed_files tồn tại
        output_dir = "processed_files"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)  # Tạo thư mục nếu chưa tồn tại
        
        # Kiểm tra quyền ghi vào thư mục
        if not os.access(output_dir, os.W_OK):
            raise PermissionError(f"Permission denied: Cannot write to {output_dir}")

        # Lưu kết quả Markdown vào file
        with open(new_file_path, "w", encoding="utf-8") as file:
            file.write(result.text_content)  # Lưu dưới dạng chuỗi Markdown

        # Nếu sử dụng MongoDB, cập nhật trạng thái
        if USE_MONGO:
            collection.update_one({"file": file_path}, {"$set": {"status": "Completed", "timestamp": time.time()}})
        
        return f"Converted to Markdown: {new_filename}"
    except Exception as e:
        # Nếu có lỗi, cập nhật trạng thái (nếu dùng MongoDB)
        if USE_MONGO:
            collection.update_one({"file": file_path}, {"$set": {"status": f"Failed: {str(e)}", "timestamp": time.time()}})
        return str(e)

# Hàm xử lý tất cả các file trong thư mục
def process_files(directory):
    files = [f for f in os.listdir(directory) if f.endswith(('.docx', '.pdf', '.pptx', '.html', '.txt', '.xlsx'))]
    total_files = len(files)

    for i, file in enumerate(files):
        file_path = os.path.join(directory, file)
        status = f"Processing {i + 1}/{total_files} - {file}"

        # Nếu sử dụng MongoDB, cập nhật trạng thái
        if USE_MONGO:
            collection.insert_one({"file": file, "status": status, "timestamp": time.time()})

        # Chuyển đổi file và trả về kết quả
        conversion_result = convert_file_to_markdown(file_path)

        # Trả về trạng thái và kết quả chuyển đổi
        yield status, conversion_result

# Tạo giao diện Gradio
def gradio_interface(directory):
    return gr.Interface(fn=process_files, inputs=gr.Textbox(), outputs=gr.Textbox())

if __name__ == "__main__":
    # Chạy giao diện Gradio và chỉ định thư mục chứa các file
    gradio_interface("data").launch()
