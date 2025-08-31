import streamlit as st
import requests

API_URL = "http://127.0.0.1:8005"  # адрес твоего FastAPI

st.set_page_config(page_title="Управление камерами и рабочими местами", layout="wide")

st.title("🎥 Управление камерами и рабочими местами")

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

tab1, tab2 = st.tabs(["Камеры", "Рабочие места"])

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
                st.markdown(
                    f"""
                            <img src="{API_URL}/cameras/{cam['id']}/snapshot"
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
# with tab2:
#     st.header("Рабочие места")
#
#     try:
#         workplaces = requests.get(f"{API_URL}/api/workplaces").json()
#     except Exception as e:
#         st.error("Ошибка подключения к API")
#         workplaces = []
#
#     for ws in workplaces:
#         with st.expander(f"👷 {ws['name']} (ID {ws['id']})"):
#             name = st.text_input("Имя", ws["name"], key=f"ws_name_{ws['id']}")
#             camera_id = st.number_input("ID камеры", value=ws["camera_id"], key=f"cam_{ws['id']}")
#             roi = st.text_input("ROI", ws["roi"], key=f"roi_{ws['id']}")
#
#             if st.button("💾 Сохранить", key=f"ws_save_{ws['id']}"):
#                 payload = {"name": name, "camera_id": camera_id, "roi": roi}
#                 requests.put(f"{API_URL}/workplaces/{ws['id']}", json=payload)
#                 st.success("Сохранено ✅")
#
#             if st.button("❌ Удалить", key=f"ws_delete_{ws['id']}"):
#                 requests.delete(f"{API_URL}/workplaces/{ws['id']}")
#                 st.warning("Удалено ❌")
#
#     st.subheader("➕ Добавить новое рабочее место")
#     new_ws_name = st.text_input("Имя нового места")
#     new_ws_camera = st.number_input("ID камеры", value=1)
#     new_ws_roi = st.text_input("ROI (x,y,w,h)")
#
#     if st.button("Добавить место"):
#         payload = {"name": new_ws_name, "camera_id": new_ws_camera, "roi": new_ws_roi}
#         requests.post(f"{API_URL}/workplaces", json=payload)
#         st.success("Место добавлено ✅")
