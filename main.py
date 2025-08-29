import cv2
import time

rtsp_url = "rtsp://admin:1qazXSW@@192.168.13.75:554/ISAPI/Streaming/Channels/101"

# Подключаемся к видеопотоку
cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("Не удалось подключиться к RTSP потоку")
    exit()

frame_counter = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Ошибка получения кадра, пробуем заново...")
        time.sleep(1)
        continue

    # Сохраняем кадр каждую секунду
    filename = f"frame_{frame_counter}.jpg"
    cv2.imwrite(filename, frame)
    print(f"Сохранен кадр: {filename}")
    frame_counter += 1

    time.sleep(1)  # ждем 1 секунду

