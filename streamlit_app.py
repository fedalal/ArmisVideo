import streamlit as st
import requests
import time
import cv2
import os
import numpy as np
from ultralytics import YOLO
from io import BytesIO
from PIL import Image

from sqlalchemy import create_engine
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from settings import settings


# создаём движок SQLAlchemy для PostgreSQL
engine = create_engine(
    settings.POSTGRES_DSN,
    echo=False,           # для отладки SQL-запросов
    future=True           # использование SQLAlchemy 2.0 style
)

API_URL = "http://192.168.13.89:8005"  # адрес твоего FastAPI
# API_URL = "http://127.0.0.1:8005"
st.set_page_config(page_title="Управление камерами и рабочими местами", layout="wide")

st.title("🎥 Управление камерами и рабочими местами")

model = YOLO("yolov10s.pt")

# отключение верхней панели
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
     <style>
        /* убираем пустое место сверху */
        .block-container {
            padding-top: 1rem; /* по умолчанию ~6rem */
        }
    </style>
    
    """,
    unsafe_allow_html=True
)

tab1, tab2, tab3 = st.tabs(["Камеры", "Рабочие места","Контроль рабочих мест"])

# ----- КАМЕРЫ -----
with tab1:
    st.header("Список камер")

    # загрузка списка камер
    try:
        cameras = requests.get(f"{API_URL}/cameras").json()
    except Exception as e:
        st.error("Ошибка подключения к API")
        cameras = []

    for cam in cameras:
        status_icon = "🟢" if cam["enabled"] else "🔴"
        with st.expander(f"📷 {cam['name']} {status_icon}"):
            name = st.text_input("Имя", cam["name"], key=f"name_{cam['id']}")
            rtsp = st.text_input("RTSP", cam["rtsp_url"], key=f"rtsp_{cam['id']}")
            interval = st.number_input("Интервал опроса камеры (сек)",  min_value=1, value=cam["poll_interval_s"], key=f"int_{cam['id']}")
            enabled = st.checkbox("Камера используется", value=cam["enabled"], key=f"enabled_{cam['id']}")

            st.markdown("---")

            # 🔹 Управление показом: snapshot или stream
            key_state = f"stream_active_{cam['id']}"
            if key_state not in st.session_state:
                st.session_state[key_state] = False  # по умолчанию поток выключен

            if not st.session_state[key_state]:
                # показываем snapshot
                cachebuster = int(time.time() * 1000)
                st.markdown(
                    f"""
                            <img src="{API_URL}/cameras/{cam['id']}/snapshot?cachebuster={cachebuster}"
                                 width="640" height="480"
                                 style="border:1px solid #ccc;"/>
                            """,
                    unsafe_allow_html=True
                )
                if st.button("▶️ Запустить поток", key=f"start_stream_{cam['id']}"):
                    st.session_state[key_state] = True
                    st.rerun()
            else:
                # показываем stream
                st.markdown(
                    f"""
                            <img src="{API_URL}/cameras/{cam['id']}/stream"
                                 width="640" height="480"
                                 style="border:1px solid #ccc;"/>
                            """,
                    unsafe_allow_html=True
                )
                if st.button("⏹ Остановить поток", key=f"stop_stream_{cam['id']}"):
                    st.session_state[key_state] = False
                    st.rerun()

            if st.button("💾 Сохранить", key=f"save_{cam['id']}"):
                payload = {"name": name, "rtsp_url": rtsp, "poll_interval_s": interval, "enabled": enabled}
                requests.put(f"{API_URL}/cameras/{cam['id']}", json=payload)
                st.success("Сохранено ✅")



            # Кнопка удалить → ставим флаг
            if st.button(f"❌ Удалить  камеру", key=f"del_{cam['id']}"):
                st.session_state[f"confirm_delete_{cam['id']}"] = True

            # Если флаг выставлен → показываем подтверждение
            if st.session_state.get(f"confirm_delete_{cam['id']}"):
                st.warning("Вы уверены, что хотите удалить эту камеру?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Да, удалить", key=f"yes_{cam['id']}"):
                        requests.delete(f"{API_URL}/cameras/{cam['id']}")
                        st.success("Удалено ❌")
                        st.session_state[f"confirm_delete_{cam['id']}"] = False
                        st.rerun()  # чтобы обновить интерфейс сразу
                with col2:
                    if st.button("❌ Отмена", key=f"no_{cam['id']}"):
                        st.session_state[f"confirm_delete_{cam['id']}"] = False
                        st.rerun()  # перезапуск интерфейса для скрытия предупреждения

    st.subheader("➕ Добавить новую камеру")
    new_name = st.text_input("Имя новой камеры")
    new_rtsp = st.text_input("RTSP новой камеры")
    new_interval = st.number_input("Интервал опроса камеры (сек)", value=10)

    if st.button("Добавить камеру"):
        payload = {"name": new_name, "rtsp_url": new_rtsp, "poll_interval_s": new_interval, "enabled" : True}
        requests.post(f"{API_URL}/cameras", json=payload)
        st.success("Камера добавлена ✅")
        for k in ["new_name", "new_rtsp", "new_interval"]:
            st.session_state[k] = "" if "name" in k or "rtsp" in k else 10
        st.rerun()

    # ----- РАБОЧИЕ МЕСТА -----
with tab2:
    st.header("Рабочие места")

    # загрузка списка рабочих мест
    try:
        workstations = requests.get(f"{API_URL}/workstations").json()
    except Exception:
        st.error("Ошибка подключения к API")
        workstations = []

    # загрузка списка камер (для выбора)
    try:
        cameras = requests.get(f"{API_URL}/cameras").json()
    except Exception:
        st.error("Ошибка подключения к API для списка камер")
        cameras = []

    camera_options = {cam["id"]: cam["name"] for cam in cameras}

    for ws in workstations:

        status_icon = "🟢" if ws["enabled"] else "🔴"

        with st.expander(f"👷 {ws['name']} {status_icon}"):
            name = st.text_input("Имя", ws["name"], key=f"ws_name_{ws['id']}")

            camera_id = st.selectbox(
                "Камера",
                options=list(camera_options.keys()),
                format_func=lambda x: f"{camera_options.get(x, 'Неизвестно')} ",
                index=list(camera_options.keys()).index(ws["camera_id"]) if ws["camera_id"] in camera_options else 0,
                key=f"ws_cam_{ws['id']}"
            )

            c1, c2, c3, c4 = st.columns(4)
            x = c1.number_input("X", min_value=0, value=int(ws["x"]), step=1, key=f"ws_x_{ws['id']}")
            y = c2.number_input("Y", min_value=0, value=int(ws["y"]), step=1, key=f"ws_y_{ws['id']}")
            w = c3.number_input("Ширина", min_value=1, value=int(ws["w"]), step=1, key=f"ws_w_{ws['id']}")
            h = c4.number_input("Высота", min_value=1, value=int(ws["h"]), step=1, key=f"ws_h_{ws['id']}")

            ws_enabled = st.checkbox("Рабочее место используется", value=ws["enabled"], key=f"ws_enabled_{ws['id']}")

            if st.button("💾 Сохранить", key=f"ws_save_{ws['id']}"):
                payload = {
                    "name": name,
                    "camera_id": int(camera_id),
                    "x": int(x),
                    "y": int(y),
                    "w": int(w),
                    "h": int(h),
                    "enabled": ws_enabled
                }
                r = requests.put(f"{API_URL}/workstations/{ws['id']}", json=payload)
                if r.status_code == 200:
                    st.success("Сохранено ✅")
                    # после сохранения обновляем картинку
                    st.session_state[f"ws_snapshot_refresh_{ws['id']}"] = True
                    st.rerun()
                else:
                    st.error(f"Ошибка: {r.text}")

            st.markdown("---")

            # создаём 2 колонки: левая под картинку, правая под кнопку
            col_img, col_btn = st.columns([1, 2])

            with col_btn:
                if st.button("🔄 Обновить", key=f"ws_refresh_{ws['id']}"):
                    st.session_state[f"ws_snapshot_refresh_{ws['id']}"] = True
                    st.rerun()
                if st.button("👁 Проверка", key=f"ws_check_{ws['id']}"):
                    url = f"{API_URL}/workstations/{ws['id']}/snapshot?cb={int(time.time())}"
                    resp = requests.get(url)
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content)).convert("RGB")
                        img_np = np.array(img)

                        results = model.predict(img_np)

                        found = False
                        roi_crop = img_np[
                                   ws["y"]: ws["y"] + ws["h"],
                                   ws["x"]: ws["x"] + ws["w"]
                                   ]

                        for r in results:
                            for box, cls, conf in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                                if int(cls) == 0:  # класс 0 = "person"
                                    x1, y1, x2, y2 = map(int, box)
                                    if (
                                            x1 >= ws["x"] and y1 >= ws["y"] and
                                            x2 <= ws["x"] + ws["w"] and
                                            y2 <= ws["y"] + ws["h"]
                                    ):
                                        found = True

                                        # переводим координаты в ROI
                                        rx1, ry1 = x1 - ws["x"], y1 - ws["y"]
                                        rx2, ry2 = x2 - ws["x"], y2 - ws["y"]

                                        # confidence в %
                                        conf_percent = f"{conf.item() * 100:.1f}%"

                                        # рисуем рамку + подпись
                                        roi_crop = roi_crop.copy()
                                        cv2.rectangle(
                                            roi_crop,
                                            (rx1, ry1),
                                            (rx2, ry2),
                                            (0, 255, 0), 2
                                        )
                                        cv2.putText(
                                            roi_crop,
                                            conf_percent,
                                            (rx1, max(ry1 - 20, 0)),
                                            cv2.FONT_HERSHEY_SIMPLEX,
                                            2,
                                            (0, 255, 0),
                                            4
                                        )
                                        break
                            if found:
                                break

                        if found:
                            st.success("✅ Человек найден в отмеченной области")
                        else:
                            st.warning("❌ Человек не найден в отмеченной области")

                        st.image(roi_crop, caption="Отмеченная область", width=320)
                    else:
                        st.error("Ошибка получения snapshot")

            # флаг для обновления изображения
            refresh_key = f"ws_snapshot_refresh_{ws['id']}"
            if refresh_key not in st.session_state:
                st.session_state[refresh_key] = True  # по умолчанию показываем

            # 🔹 Управление показом: snapshot или stream
            key_state = f"ws_stream_active_{ws['id']}"
            if key_state not in st.session_state:
                st.session_state[key_state] = False  # по умолчанию поток выключен

            if st.session_state[refresh_key]:
                with col_img:
                    cachebuster = int(time.time() * 1000)
                    st.markdown(
                        f"""
                                <img src="{API_URL}/workstations/{ws['id']}/snapshot?cachebuster={cachebuster}"
                                     width="640" height="480"
                                     style="border:1px solid #ccc;"/>
                                """,
                        unsafe_allow_html=True
                    )
                # сбрасываем, чтобы картинка не грузилась бесконечно заново
                st.session_state[refresh_key] = False



            # Удаление с подтверждением
            if st.button("❌ Удалить рабочее место", key=f"ws_del_{ws['id']}"):
                st.session_state[f"confirm_ws_delete_{ws['id']}"] = True

            if st.session_state.get(f"confirm_ws_delete_{ws['id']}"):
                st.warning("Вы уверены, что хотите удалить это рабочее место?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Да, удалить", key=f"ws_yes_{ws['id']}"):
                        requests.delete(f"{API_URL}/workstations/{ws['id']}")
                        st.success("Удалено ❌")
                        st.session_state[f"confirm_ws_delete_{ws['id']}"] = False
                        st.rerun()
                with col2:
                    if st.button("❌ Отмена", key=f"ws_no_{ws['id']}"):
                        st.session_state[f"confirm_ws_delete_{ws['id']}"] = False
                        st.rerun()

    st.subheader("➕ Добавить новое рабочее место")
    new_ws_name = st.text_input("Имя нового места", key="new_ws_name")
    new_ws_camera = st.selectbox(
        "Камера",
        options=list(camera_options.keys()),
        format_func=lambda x: f"{camera_options.get(x, 'Неизвестно')}",
        key="new_ws_camera"
    )

    c1, c2, c3, c4 = st.columns(4)
    new_x = c1.number_input("X", min_value=0, value=0, step=1, key="new_ws_x")
    new_y = c2.number_input("Y", min_value=0, value=0, step=1, key="new_ws_y")
    new_w = c3.number_input("Ширина", min_value=1, value=100, step=1, key="new_ws_w")
    new_h = c4.number_input("Высота", min_value=1, value=100, step=1, key="new_ws_h")

    if st.button("Добавить место"):
        payload = {
            "name": new_ws_name,
            "camera_id": int(new_ws_camera),
            "x": int(new_x),
            "y": int(new_y),
            "w": int(new_w),
            "h": int(new_h),
            "enabled":True
        }
        r = requests.post(f"{API_URL}/workstations", json=payload)
        if r.status_code == 200:
            st.success("Место добавлено ✅")
            # очистка полей
            # st.session_state["new_ws_name"] = ""
            # st.session_state["new_ws_camera"] = list(camera_options.keys())[0] if camera_options else 1
            # st.session_state["new_ws_x"] = 0
            # st.session_state["new_ws_y"] = 0
            # st.session_state["new_ws_w"] = 100
            # st.session_state["new_ws_h"] = 100
            st.rerun()
        else:
            st.error(f"Ошибка: {r.text}")
with tab3:
    st.header("📊 Контроль рабочих мест")

    col1, col2, col3, col4, col5 = st.columns(5)

    df_ws = pd.read_sql("select name from workstations order by 1", engine)


    with col1:
        # фильтр по рабочему месту
        ws_options = ["Все"] + sorted(df_ws["name"].unique().tolist())
        ws_filter = st.selectbox("Рабочее место", ws_options)
        ws_condition = ''
        if ws_filter != "Все":
            ws_condition =' AND w.name = ' + "'" + ws_filter + "'"

    with col2:
        # фильтр по дате
        start_date = st.date_input("Дата начала")

    with col3:
        # фильтр по дате
        end_date = st.date_input("Дата окончания")

    with col4:
        # фильтр по наличию человека
        found_filter = st.selectbox("Наличие человека", ["Все", "Найден", "Не найден"])
        people_condition = ''
        if found_filter == "Найден":
            people_condition = ' AND f.people_count > 0 '
        elif found_filter == "Не найден":
            people_condition = ' AND f.people_count = 0 '

    with col5:
        # фильтр по проценту
        conf_min, conf_max = st.slider("Диапазон процента уверенности", 0, 100, (0, 100))

    try:

        query = f"""
            SELECT f.id,
                   w.name AS workstation_name,
                   f.captured_at,
                   f.people_count,
                   f.conf,
                   f.thumb_path
            FROM frames f
            LEFT JOIN workstations w ON f.workstation_id = w.id
            WHERE f.captured_at::date BETWEEN '{start_date.strftime("%Y-%m-%d")}' 
                                          AND '{end_date.strftime("%Y-%m-%d")}'
                AND f.conf BETWEEN '{conf_min}' AND '{conf_max}'
                 {people_condition}
                 {ws_condition}
            ORDER BY f.id DESC
        """
        df = pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Ошибка подключения к базе: {e}")
        df = pd.DataFrame()

    if not df.empty:
        # преобразуем timestamp
        df["captured_at"] = pd.to_datetime(df["captured_at"])











        # переименуем колонки
        df = df.rename(columns={
            "workstation_name": "Рабочее место",
            "trigger" : "Событие",
            "conf": "Уверенность (%)",
            "thumb_path": "Миниатюра"
        })

        # Рендерер для колонки ЛюдейНайдено
        people_renderer = JsCode("""
        function(params) {
            if (!params.value || params.value === 0) {
                return '❌';
            } else {
                let result = '';
                for (let i = 0; i < params.value; i++) {
                    result += '✅';
                }
                return result;
            }
        }
        """)

        # Рендерер для форматирования даты
        date_renderer = JsCode("""
        function(params) {
            if (!params.value) return '';
            const dt = new Date(params.value);   // преобразуем строку в JS Date
            const dd = String(dt.getDate()).padStart(2, '0');
            const mm = String(dt.getMonth() + 1).padStart(2, '0');
            const yy = String(dt.getFullYear()).slice(-2);
            const hh = String(dt.getHours()).padStart(2, '0');
            const mi = String(dt.getMinutes()).padStart(2, '0');
            const ss = String(dt.getSeconds()).padStart(2, '0');
            return `${dd}.${mm}.${yy} ${hh}:${mi}:${ss}`;
        }
        """)

        thumbnail_renderer = JsCode("""
               class ThumbnailRenderer {
    init(params) {
        this.eGui = document.createElement('div'); // Create a container div
        this.eGui.style.display = 'flex'; // Set display to flex
        this.eGui.style.justifyContent = 'center'; // Center horizontally
        this.eGui.style.alignItems = 'center'; // Center vertically
        
        const eyeIcon = document.createElement('span');
        // создаём иконку "глаз"
         eyeIcon.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
                 stroke="currentColor" width="22" height="22" style="cursor:pointer;">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 
                       4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>`;
        this.eGui.appendChild(eyeIcon);
        
            
        // Add event listener for click event on the image
        eyeIcon.addEventListener('click', () => {
            // Create a modal or popover to display the enlarged image
            const modal = document.createElement('div');
            modal.style.position = 'fixed';
            modal.style.top = '0';
            modal.style.left = '0';
            modal.style.width = '100%';
            modal.style.height = '100%';
            modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
            modal.style.display = 'flex';
            modal.style.justifyContent = 'center';
            modal.style.alignItems = 'center';

            const enlargedImg = document.createElement('img');
            enlargedImg.setAttribute('src', '
            """ + API_URL + """/images/' +params.value);
            enlargedImg.style.maxWidth = '90%';
            enlargedImg.style.maxHeight = '90%';

            modal.appendChild(enlargedImg);

            // Close modal when clicking outside the image
            modal.addEventListener('click', (event) => {
                if (event.target === modal) {
                    modal.remove();
                }
            });

            document.body.appendChild(modal);
        });
    }

    getGui() {
        return this.eGui;
    }
}
           """)

        # JS для найден/не найден
        found_renderer = JsCode("""
        function(params) {
            return params.value ? "✅" : "❌";
        }
        """)

        # итоговая таблица
        # st.dataframe(df.sort_values(by="ID", ascending=False), width='stretch')
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_column("Миниатюра", cellRenderer=thumbnail_renderer)
        gb.configure_column("id", header_name="ID",  valueGetter=JsCode("function(params) { return parseInt(params.data.id) || params.data.id; }"), type=["numericColumn", "leftAligned"], sortable=True)
        # Настраиваем колонку "captured_at"
        gb.configure_column(
            "captured_at",
            header_name="Дата/Время",
            cellRenderer=date_renderer,
            sortable=True
        )
        gb.configure_column(
            "people_count",  # имя колонки в DataFrame
            header_name="Людей Найдено",
            cellRenderer=people_renderer,
            sortable=True,
            filter=True
        )

        grid_options = gb.build()

        AgGrid(df, gridOptions=grid_options,
               allow_unsafe_jscode=True,
               enable_enterprise_modules=False,
               fit_columns_on_grid_load=True,
               height=600
               )
    else:
        st.info("Нет данных для отображения")
