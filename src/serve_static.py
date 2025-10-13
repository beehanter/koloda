# src/serve_static.py
import http.server
import socketserver
import os

# Определяем порт и директорию
PORT = 8001
# Путь к директории storage относительно корня проекта
# Скрипт запускается из корня, поэтому путь должен быть 'storage'
# Но если он запускается из src, путь должен быть '../storage'
# Сделаем его более надежным
CWD = os.getcwd()
# Предполагаем, что корень проекта - это там, где лежит папка 'storage'
PROJECT_ROOT = CWD if 'storage' in os.listdir(CWD) else os.path.dirname(CWD)
DIRECTORY = os.path.join(PROJECT_ROOT, "storage")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # SimpleHTTPRequestHandler не принимает 'directory' в Python < 3.7
        # Но в современных версиях это лучший способ
        # Для надежности, мы можем сделать chdir, но это менее безопасно
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

# Запускаем сервер
try:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Сервер для статических файлов запущен на порту {PORT}")
        print(f"Раздает файлы из директории: {os.path.abspath(DIRECTORY)}")
        httpd.serve_forever()
except FileNotFoundError:
    print(f"ОШИБКА: Директория '{DIRECTORY}' не найдена.")
    print("Убедитесь, что вы запускаете скрипт из корневой директории проекта или из папки 'src'.")
