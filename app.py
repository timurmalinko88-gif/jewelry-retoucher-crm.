"""Main Streamlit Application for Retoucher CRM.

Complete offline-first CRM for jewelry freelance retoucher.
"""

from datetime import date, datetime
import io
import sqlite3
import urllib.parse
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd

from db import execute_query, fetch_all, fetch_one, get_connection, get_dataframe, init_db, seed_demo_data
from gmail_drafts import (
    OUTREACH_TEMPLATES,
    create_gmail_draft,
    is_gmail_configured,
    render_template,
)
from logic import (
    calculate_next_action_date,
    detect_cultural_profile,
    get_contact_touch_count,
    parse_and_import_contacts_json,
)
from theme import (
    LUXURY_BENTO_CSS,
    inject_luxury_theme,
    render_atelier_header,
    render_horlogerie_clocks,
)

# Page config
st.set_page_config(
    page_title="Retoucher CRM | Atelier Joaillerie",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Haute Joaillerie Atelier Bento Design System
inject_luxury_theme()

# Ensure database exists
init_db()
# seed_demo_data()  # Disabled to keep database clean

# ==============================================================================
# SIDEBAR: Timezones & Outreach Configuration
# ==============================================================================
with st.sidebar:
    st.markdown("### 🌍 Horlogerie: Часовые пояса")
    st.caption("Ориентир для отправки follow-up в рабочее время клиента")

    tz_targets = [
        ("🇺🇸 New York (EST)", "America/New_York"),
        ("🇬🇧 London (GMT/BST)", "Europe/London"),
        ("🇫🇷 Paris (CET)", "Europe/Paris"),
        ("🇦🇪 Dubai (GST)", "Asia/Dubai"),
        ("🇯🇵 Tokyo (JST)", "Asia/Tokyo"),
    ]
    render_horlogerie_clocks(tz_targets)

    st.markdown("---")
    st.markdown("### ⚙️ Настройки аутрича")
    if "sender_name" not in st.session_state:
        st.session_state["sender_name"] = "Тимур"
    if "portfolio_link" not in st.session_state:
        st.session_state["portfolio_link"] = "https://behance.net/gallery/jewelry-retouch"

    s_name = st.text_input("Ваше имя (в подписи):", value=st.session_state["sender_name"], key="cfg_s_name")
    st.session_state["sender_name"] = s_name

    s_port = st.text_input("Ссылка на портфолио:", value=st.session_state["portfolio_link"], key="cfg_s_port")
    st.session_state["portfolio_link"] = s_port

    st.markdown("---")
    st.markdown("### ☁️ Облако Supabase")
    from supabase_sync import is_supabase_connected, push_to_supabase, pull_from_supabase

    if is_supabase_connected():
        st.success("🟢 Supabase подключен")
        c_sync1, c_sync2 = st.columns(2)
        with c_sync1:
            if st.button("⬆️ В облако", key="btn_push_cloud", help="Отправить все локальные данные в Supabase"):
                res = push_to_supabase()
                if res["success"]:
                    st.toast("✅ База успешно выгружена в Supabase!")
                else:
                    st.error("Ошибка выгрузки в облако")
        with c_sync2:
            if st.button("⬇️ Из облака", key="btn_pull_cloud", help="Загрузить актуальные данные из Supabase"):
                res = pull_from_supabase()
                if res["success"]:
                    st.toast("✅ База обновлена из Supabase!")
                    st.rerun()
                else:
                    st.error("Ошибка загрузки из облака")
    else:
        st.info("⚪ Офлайн-режим (SQLite)")

# App Header: Haute Joaillerie Atelier Bento Header
today_str = date.today().isoformat()
render_atelier_header(date_str=date.today().strftime("%d.%m.%Y"))

# Navigation Tabs
tab_today, tab_contacts, tab_outreach, tab_deals, tab_money, tab_dashboard = st.tabs(
    [
        "⚡ TODAY",
        "👥 CONTACTS",
        "🚀 OUTREACH",
        "💼 DEALS",
        "💰 MONEY",
        "📊 DASHBOARD",
    ]
)

# ==============================================================================
# TAB 1: TODAY
# ==============================================================================
with tab_today:
    touches_query = """
        SELECT 
            t.id AS touch_id,
            t.contact_id,
            c.brand_name,
            c.country,
            c.cultural_profile,
            c.pipeline_status,
            t.channel,
            t.subject,
            t.next_action_date,
            t.notes
        FROM touches t
        JOIN contacts c ON t.contact_id = c.id
        WHERE t.next_action_date IS NOT NULL 
          AND t.next_action_date <= ?
        ORDER BY t.next_action_date ASC
    """
    due_touches = fetch_all(touches_query, (today_str,))

    retainers_query = """
        SELECT 
            r.id AS retainer_id,
            r.contact_id,
            c.brand_name,
            r.monthly_amount_usd,
            r.images_per_month,
            r.next_contract_ping_date,
            r.status
        FROM retainers r
        JOIN contacts c ON r.contact_id = c.id
        WHERE r.status = 'active'
          AND r.next_contract_ping_date IS NOT NULL
          AND r.next_contract_ping_date <= ?
        ORDER BY r.next_contract_ping_date ASC
    """
    due_retainers = fetch_all(retainers_query, (today_str,))

    deals_query = """
        SELECT 
            d.id AS deal_id,
            d.contact_id,
            c.brand_name,
            d.description,
            d.amount_usd,
            d.delivered_date,
            d.upwork_contract_url,
            d.status
        FROM deals d
        JOIN contacts c ON d.contact_id = c.id
        WHERE d.status = 'in_progress'
        ORDER BY d.delivered_date ASC
    """
    active_deals = fetch_all(deals_query)

    # Top KPI summary cards
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        overdue_cnt = sum(1 for t in due_touches if t["next_action_date"] < today_str)
        st.metric(
            label="Касания / Follow-up",
            value=f"{len(due_touches)} в плане",
            delta=f"-{overdue_cnt} просрочено" if overdue_cnt > 0 else "все вовремя",
            delta_color="inverse" if overdue_cnt > 0 else "normal",
        )
    with col_kpi2:
        st.metric(
            label="Пинги ретейнеров",
            value=f"{len(due_retainers)} на очереди",
        )
    with col_kpi3:
        st.metric(
            label="Сделки в работе (Deadline)",
            value=f"{len(active_deals)} активных",
        )

    st.markdown("---")

    col_left, col_right = st.columns([3, 2], gap="medium")

    # Left Column: Operational queues
    with col_left:
        st.subheader("📋 Касания на контроле (Overdue & Today)")
        if not due_touches:
            st.success("🎉 Все запланированные касания выполнены! Нет просроченных задач.")
        else:
            for item in due_touches:
                is_overdue = item["next_action_date"] < today_str
                status_label = f"🔴 Просрочено ({item['next_action_date']})" if is_overdue else f"🟡 На сегодня ({item['next_action_date']})"

                with st.expander(f"{status_label} — **{item['brand_name']}** ({item['country'] or 'Global'})", expanded=True):
                    st.write(f"**Канал:** {item['channel']} | **Культурный профиль:** `{item['cultural_profile']}`")
                    if item["subject"]:
                        st.write(f"**Тема/Цель:** {item['subject']}")
                    if item["notes"]:
                        st.caption(f"Заметка: {item['notes']}")

                    if st.button("✅ Отметить выполненным", key=f"done_touch_{item['touch_id']}"):
                        execute_query(
                            "UPDATE touches SET next_action_date = NULL, status = 'completed' WHERE id = ?",
                            (item["touch_id"],),
                        )
                        st.toast(f"Касание для {item['brand_name']} закрыто!")
                        st.rerun()

        st.markdown("### 🔔 Пинги ретейнеров (Monthly retainers)")
        if not due_retainers:
            st.info("Нет активных ретейнеров, требующих подтверждения на сегодня.")
        else:
            for ret in due_retainers:
                st.warning(
                    f"**{ret['brand_name']}**: ретейнер ${ret['monthly_amount_usd']:.0f}/мес "
                    f"({ret['images_per_month']} фото). Дата контрольного пинга: **{ret['next_contract_ping_date']}**"
                )

        st.markdown("### ⏳ Ожидают сдачи (Active Deals)")
        if not active_deals:
            st.info("Сейчас нет сделок в статусе 'in_progress'.")
        else:
            for deal in active_deals:
                deadline_note = f"Срок сдачи: **{deal['delivered_date'] or 'не указан'}**"
                upwork_btn = f" | [Upwork Contract]({deal['upwork_contract_url']})" if deal["upwork_contract_url"] else ""
                st.info(
                    f"**{deal['brand_name']}** — ${deal['amount_usd']:.0f} "
                    f"({deal['description'] or 'Ретушь'}) | {deadline_note}{upwork_btn}"
                )

    # Right Column: Quick Touch Logging
    with col_right:
        st.subheader("⚡ Быстрое логирование касания")
        st.caption("Минимум кликов: выберите контакт, канал и результат. Каденция рассчитается сама.")

        contacts_rows = fetch_all("SELECT id, brand_name, cultural_profile, pipeline_status FROM contacts ORDER BY brand_name ASC")
        if not contacts_rows:
            st.warning("В базе нет контактов. Добавьте контакты во вкладке CONTACTS.")
        else:
            contact_options = {
                f"{r['brand_name']} ({r['cultural_profile']}, status: {r['pipeline_status']})": r["id"]
                for r in contacts_rows
            }
            selected_label = st.selectbox("1. Контакт (Бренд):", options=list(contact_options.keys()), key="quick_touch_contact")
            selected_contact_id = contact_options[selected_label]

            contact_data = fetch_one("SELECT * FROM contacts WHERE id = ?", (selected_contact_id,))
            contact_profile = contact_data["cultural_profile"] if contact_data else "standard"
            touch_count = get_contact_touch_count(selected_contact_id)

            col_ch, col_subj = st.columns(2)
            with col_ch:
                channel = st.selectbox(
                    "2. Канал связи:",
                    options=["Email", "Instagram", "LinkedIn", "Upwork", "WhatsApp"],
                    key="quick_channel",
                )
            with col_subj:
                template_type = st.selectbox(
                    "Шаблон / Тип:",
                    options=[
                        "initial_cold",
                        "portfolio_followup",
                        "case_study_drop",
                        "pricing_quote",
                        "breakup_email",
                        "custom",
                    ],
                    key="quick_template",
                )

            touch_notes = st.text_area(
                "3. Результат / Заметка:",
                placeholder="Напр., Отправил превью ретуши 3 колец, попросил обратную связь.",
                height=90,
                key="quick_notes",
            )

            calc_touch_num = touch_count + 1
            default_next_date = calculate_next_action_date(
                contact_profile,
                date.today(),
                touch_number=calc_touch_num,
            )

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                next_date_val = st.date_input(
                    f"Следующий контакт ({contact_profile}):",
                    value=default_next_date if default_next_date else date.today(),
                    key="quick_next_date",
                )
            with col_d2:
                pipeline_options = ["lead", "contacted", "replied", "negotiation", "closed_won", "closed_lost"]
                current_p_status = contact_data["pipeline_status"] if contact_data else "lead"
                default_idx = 1 if current_p_status == "lead" else (
                    pipeline_options.index(current_p_status) if current_p_status in pipeline_options else 0
                )
                new_status = st.selectbox(
                    "Новый статус pipeline:",
                    options=pipeline_options,
                    index=default_idx,
                    key="quick_pipeline_status",
                )

            if st.button("🚀 Зафиксировать касание", use_container_width=True, type="primary", key="quick_save_btn"):
                execute_query(
                    """
                    INSERT INTO touches (
                        contact_id, channel, template_type, subject, sent_date,
                        status, next_action_date, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        selected_contact_id,
                        channel,
                        template_type,
                        f"Touch #{calc_touch_num} via {channel}",
                        today_str,
                        "sent",
                        next_date_val.isoformat() if next_date_val else None,
                        touch_notes,
                    ),
                )

                execute_query(
                    """
                    UPDATE contacts 
                    SET pipeline_status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_status, selected_contact_id),
                )

                st.success(f"Касание сохранено! Следующее действие: {next_date_val.strftime('%d.%m.%Y') if next_date_val else 'Не запланировано'}")
                st.rerun()

# ==============================================================================
# TAB 2: CONTACTS
# ==============================================================================
with tab_contacts:
    st.subheader("👥 База контактов и брендов")

    # Tools row (Import / Export / New contact)
    with st.expander("⚙️ Действия с базой: Импорт JSON / Экспорт CSV / Новый контакт", expanded=False):
        t_col1, t_col2 = st.columns(2)

        # JSON Import Section
        with t_col1:
            st.markdown("#### 📥 Импорт из JSON (с защитой от дублей)")
            st.caption("Поддерживает вложенный формат `global_master.json` и плоские списки. Дубли по сайту и email отсеиваются.")
            uploaded_file = st.file_uploader("Выберите .json файл", type=["json"], key="json_uploader")
            raw_json_input = st.text_area(
                "Или вставьте JSON строкой напрямую:",
                placeholder='[{"brand_name": "Studio Gold", "website": "studiogold.com", "email": "info@studiogold.com"}]',
                height=80,
                key="raw_json_textarea",
            )
            source_tag = st.text_input("Метка источника (source_base):", value="Import", key="import_source_tag")

            if st.button("Запустить импорт", key="run_import_btn", type="primary"):
                content = None
                if uploaded_file is not None:
                    try:
                        content = uploaded_file.read().decode("utf-8")
                    except Exception as e:
                        st.error(f"Ошибка чтения файла: {e}")
                elif raw_json_input.strip():
                    content = raw_json_input.strip()

                if content:
                    result = parse_and_import_contacts_json(content, default_source=source_tag)
                    if result["success"]:
                        st.success(
                            f"✅ Импорт завершен! Добавлено новых: **{result['imported']}**, "
                            f"Пропущено дубликатов: **{result['duplicates']}**."
                        )
                        if result["errors"]:
                            st.warning(f"Ошибок строк: {len(result['errors'])}")
                        st.rerun()
                    else:
                        st.error(f"Ошибка импорта: {result.get('error')}")
                else:
                    st.warning("Загрузите файл или вставьте JSON текст.")

        # Manual New Contact
        with t_col2:
            st.markdown("#### ➕ Добавить бренд вручную")
            with st.form("add_contact_manual_form"):
                m_brand = st.text_input("Название бренда *", placeholder="Tiffany & Co")
                c1, c2 = st.columns(2)
                with c1:
                    m_country = st.text_input("Страна (US, GB, FR, IT...):", value="US")
                    m_website = st.text_input("Вебсайт:", placeholder="https://brand.com")
                    m_email = st.text_input("Email:", placeholder="contact@brand.com")
                with c2:
                    m_priority = st.selectbox("Приоритет:", ["high", "medium", "low"], index=1)
                    m_culture = st.selectbox(
                        "Культурный профиль:",
                        ["aggressive", "standard", "patient", "slow"],
                        index=["aggressive", "standard", "patient", "slow"].index(detect_cultural_profile(m_country)),
                    )
                    m_status = st.selectbox("Pipeline статус:", ["lead", "contacted", "replied", "negotiation", "closed_won"])

                m_decision = st.text_input("Лицо принимающее решение (ДПР):", placeholder="Art Director / Founder")
                m_notes = st.text_area("Заметки:", placeholder="Особенности съемки, требования к ретуши...", height=70)

                submit_new = st.form_submit_button("Сохранить контакт")
                if submit_new:
                    if not m_brand.strip():
                        st.error("Укажите название бренда!")
                    else:
                        execute_query(
                            """
                            INSERT INTO contacts (
                                brand_name, country, website, email, priority,
                                cultural_profile, pipeline_status, decision_maker, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                m_brand.strip(),
                                m_country.strip().upper(),
                                m_website.strip(),
                                m_email.strip().lower(),
                                m_priority,
                                m_culture,
                                m_status,
                                m_decision.strip(),
                                m_notes.strip(),
                            ),
                        )
                        st.success(f"Контакт '{m_brand}' успешно добавлен!")
                        st.rerun()

    # Filters row
    st.markdown("#### 🔍 Фильтры и поиск")
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([3, 2, 2, 2, 2])
    with f_col1:
        search_query = st.text_input("Поиск (бренд, email, сайт):", placeholder="Введите название...", key="search_query")
    with f_col2:
        status_filter = st.selectbox(
            "Статус pipeline:",
            ["Все", "lead", "contacted", "replied", "negotiation", "closed_won", "closed_lost"],
            key="status_filter",
        )
    with f_col3:
        priority_filter = st.selectbox("Приоритет:", ["Все", "high", "medium", "low"], key="priority_filter")
    with f_col4:
        culture_filter = st.selectbox(
            "Каденция (культура):",
            ["Все", "aggressive", "standard", "patient", "slow"],
            key="culture_filter",
        )
    with f_col5:
        # Dynamic country list from DB
        countries_raw = fetch_all("SELECT DISTINCT country FROM contacts WHERE country IS NOT NULL AND country != '' ORDER BY country")
        country_options = ["Все"] + [c["country"] for c in countries_raw]
        country_filter = st.selectbox("Страна:", country_options, key="country_filter")

    # Build SQL Query based on filters
    sql_base = """
        SELECT 
            c.id,
            c.brand_name,
            c.country,
            c.website,
            c.email,
            c.priority,
            c.cultural_profile,
            c.pipeline_status,
            c.decision_maker,
            (SELECT COUNT(*) FROM touches WHERE contact_id = c.id) AS touches_count,
            c.updated_at
        FROM contacts c
        WHERE 1=1
    """
    params = []

    if search_query.strip():
        sql_base += " AND (c.brand_name LIKE ? OR c.email LIKE ? OR c.website LIKE ?)"
        term = f"%{search_query.strip()}%"
        params.extend([term, term, term])

    if status_filter != "Все":
        sql_base += " AND c.pipeline_status = ?"
        params.append(status_filter)

    if priority_filter != "Все":
        sql_base += " AND c.priority = ?"
        params.append(priority_filter)

    if culture_filter != "Все":
        sql_base += " AND c.cultural_profile = ?"
        params.append(culture_filter)

    if country_filter != "Все":
        sql_base += " AND c.country = ?"
        params.append(country_filter)

    sql_base += " ORDER BY c.id DESC"
    contacts_df = get_dataframe(sql_base, params=tuple(params))

    # Display count and Export Button
    col_cnt, col_exp = st.columns([4, 1])
    with col_cnt:
        st.write(f"Найдено записей: **{len(contacts_df)}**")
    with col_exp:
        if not contacts_df.empty:
            csv_buffer = io.StringIO()
            contacts_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Скачать в CSV",
                data=csv_buffer.getvalue(),
                file_name=f"contacts_export_{date.today().isoformat()}.csv",
                mime="text/csv",
                key="download_csv_btn",
            )

    # Main Interactive Dataframe
    if contacts_df.empty:
        st.info("По заданным критериям фильтра контакты не найдены.")
    else:
        st.dataframe(
            contacts_df,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "brand_name": st.column_config.TextColumn("Бренд", width="medium"),
                "country": st.column_config.TextColumn("Страна", width="small"),
                "website": st.column_config.LinkColumn("Сайт", width="medium"),
                "email": st.column_config.TextColumn("Email", width="medium"),
                "priority": st.column_config.TextColumn("Приоритет", width="small"),
                "cultural_profile": st.column_config.TextColumn("Каденция", width="small"),
                "pipeline_status": st.column_config.TextColumn("Статус", width="small"),
                "touches_count": st.column_config.NumberColumn("Касаний", width="small"),
                "updated_at": st.column_config.TextColumn("Обновлен", width="medium"),
            },
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    # ==============================================================================
    # Contact Detail Card (View, Edit, History)
    # ==============================================================================
    st.subheader("📇 Карточка контакта (Редактирование и История)")

    all_contacts_for_card = fetch_all("SELECT id, brand_name, country FROM contacts ORDER BY brand_name ASC")
    if not all_contacts_for_card:
        st.info("Контакты отсутствуют.")
    else:
        card_choices = {f"#{c['id']} — {c['brand_name']} ({c['country'] or 'Global'})": c["id"] for c in all_contacts_for_card}
        selected_card_label = st.selectbox("Выберите контакт для просмотра деталей:", options=list(card_choices.keys()), key="select_card_contact")
        card_contact_id = card_choices[selected_card_label]

        contact_detail = fetch_one("SELECT * FROM contacts WHERE id = ?", (card_contact_id,))
        if contact_detail:
            col_card_info, col_card_hist = st.columns([3, 2], gap="large")

            # Left: Edit Form
            with col_card_info:
                st.markdown(f"### Редактирование: **{contact_detail['brand_name']}**")
                with st.form(f"edit_contact_form_{card_contact_id}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        edit_brand = st.text_input("Бренд:", value=contact_detail["brand_name"])
                        edit_country = st.text_input("Страна:", value=contact_detail["country"] or "")
                        edit_website = st.text_input("Веб-сайт:", value=contact_detail["website"] or "")
                        edit_insta = st.text_input("Instagram:", value=contact_detail["instagram"] or "")
                        edit_email = st.text_input("Email:", value=contact_detail["email"] or "")
                    with e2:
                        edit_decision = st.text_input("Лицо принимающее решение:", value=contact_detail["decision_maker"] or "")
                        edit_priority = st.selectbox(
                            "Приоритет:",
                            ["high", "medium", "low"],
                            index=["high", "medium", "low"].index(contact_detail["priority"]) if contact_detail["priority"] in ["high", "medium", "low"] else 1,
                        )
                        edit_culture = st.selectbox(
                            "Культурный профиль:",
                            ["aggressive", "standard", "patient", "slow"],
                            index=["aggressive", "standard", "patient", "slow"].index(contact_detail["cultural_profile"]) if contact_detail["cultural_profile"] in ["aggressive", "standard", "patient", "slow"] else 1,
                        )
                        edit_status = st.selectbox(
                            "Pipeline статус:",
                            ["lead", "contacted", "replied", "negotiation", "closed_won", "closed_lost"],
                            index=["lead", "contacted", "replied", "negotiation", "closed_won", "closed_lost"].index(contact_detail["pipeline_status"]) if contact_detail["pipeline_status"] in ["lead", "contacted", "replied", "negotiation", "closed_won", "closed_lost"] else 0,
                        )
                        edit_catalog = st.text_input("Каталог / Объем:", value=contact_detail["catalog_size"] or "")

                    edit_photo = st.text_input("Оценка фото / задач ретуши:", value=contact_detail["photo_quality"] or "")
                    edit_notes = st.text_area("Заметки:", value=contact_detail["notes"] or "", height=80)

                    c_save, c_del = st.columns([4, 1])
                    with c_save:
                        save_btn = st.form_submit_button("💾 Сохранить изменения", type="primary")
                    with c_del:
                        delete_btn = st.form_submit_button("🗑️ Удалить", type="secondary")

                    if save_btn:
                        execute_query(
                            """
                            UPDATE contacts SET
                                brand_name = ?, country = ?, website = ?, instagram = ?,
                                email = ?, decision_maker = ?, priority = ?, cultural_profile = ?,
                                pipeline_status = ?, catalog_size = ?, photo_quality = ?,
                                notes = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (
                                edit_brand, edit_country, edit_website, edit_insta,
                                edit_email, edit_decision, edit_priority, edit_culture,
                                edit_status, edit_catalog, edit_photo, edit_notes,
                                card_contact_id,
                            ),
                        )
                        st.toast("Изменения сохранены!")
                        st.rerun()

                    if delete_btn:
                        execute_query("DELETE FROM contacts WHERE id = ?", (card_contact_id,))
                        st.toast(f"Контакт {contact_detail['brand_name']} удален!")
                        st.rerun()

            # Right: Touch & Deal History
            with col_card_hist:
                st.markdown("### 📜 История касаний (Touches)")
                contact_touches = fetch_all(
                    "SELECT * FROM touches WHERE contact_id = ? ORDER BY sent_date DESC, id DESC",
                    (card_contact_id,),
                )
                if not contact_touches:
                    st.info("Касаний по этому контакту пока не зафиксировано.")
                else:
                    for t in contact_touches:
                        st.markdown(
                            f"**{t['sent_date']}** | `{t['channel']}` ({t['template_type'] or 'direct'})\n\n"
                            f"*{t['subject']}*\n\n"
                            f"> {t['notes'] or 'Без заметок'}\n\n"
                            f"След. действие: `{t['next_action_date'] or 'завершено'}`"
                        )
                        st.markdown("---")

                st.markdown("### 💼 Связанные сделки (Deals)")
                contact_deals = fetch_all(
                    "SELECT * FROM deals WHERE contact_id = ? ORDER BY created_date DESC",
                    (card_contact_id,),
                )
                if not contact_deals:
                    st.caption("Сделок пока нет.")
                else:
                    for d in contact_deals:
                        st.write(
                            f"💰 **${d['amount_usd']:.0f}** — {d['description'] or 'Ретушь'} "
                            f"(Статус: `{d['status']}`, Срок: {d['delivered_date'] or '—'})"
                        )

# ==============================================================================
# TAB 3: OUTREACH
# ==============================================================================
with tab_outreach:
    st.subheader("🚀 Воронка Outreach и Канбан-доска")

    # Fetch contacts with touch counts and latest touch dates
    outreach_query = """
        SELECT 
            c.id,
            c.brand_name,
            c.country,
            c.website,
            c.email,
            c.priority,
            c.cultural_profile,
            c.pipeline_status,
            c.category,
            (SELECT COUNT(*) FROM touches WHERE contact_id = c.id) AS touches_count,
            (SELECT MAX(sent_date) FROM touches WHERE contact_id = c.id) AS last_touch_date,
            (SELECT next_action_date FROM touches WHERE contact_id = c.id AND next_action_date IS NOT NULL ORDER BY next_action_date ASC LIMIT 1) AS next_action_date
        FROM contacts c
        ORDER BY c.id DESC
    """
    all_outreach_contacts = fetch_all(outreach_query)

    # Calculate funnel metrics
    total_contacts_cnt = len(all_outreach_contacts)
    untouched_contacts = [c for c in all_outreach_contacts if c["touches_count"] == 0]
    untouched_cnt = len(untouched_contacts)

    stage_counts = {
        "lead": sum(1 for c in all_outreach_contacts if c["pipeline_status"] == "lead"),
        "contacted": sum(1 for c in all_outreach_contacts if c["pipeline_status"] == "contacted"),
        "replied": sum(1 for c in all_outreach_contacts if c["pipeline_status"] == "replied"),
        "negotiation": sum(1 for c in all_outreach_contacts if c["pipeline_status"] == "negotiation"),
        "closed_won": sum(1 for c in all_outreach_contacts if c["pipeline_status"] == "closed_won"),
        "closed_lost": sum(1 for c in all_outreach_contacts if c["pipeline_status"] == "closed_lost"),
    }

    touched_total = (
        stage_counts["contacted"]
        + stage_counts["replied"]
        + stage_counts["negotiation"]
        + stage_counts["closed_won"]
        + stage_counts["closed_lost"]
    )

    response_positive = stage_counts["replied"] + stage_counts["negotiation"] + stage_counts["closed_won"]
    response_rate = (response_positive / touched_total * 100.0) if touched_total > 0 else 0.0
    win_rate = (stage_counts["closed_won"] / touched_total * 100.0) if touched_total > 0 else 0.0

    # Metrics Row
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1:
        st.metric("Всего брендов", total_contacts_cnt)
    with m_col2:
        st.metric(
            "База без касаний",
            untouched_cnt,
            delta=f"{(untouched_cnt / total_contacts_cnt * 100):.0f}% базы" if total_contacts_cnt > 0 else "0%",
            delta_color="off",
        )
    with m_col3:
        st.metric("В процессе диалога", stage_counts["replied"] + stage_counts["negotiation"])
    with m_col4:
        st.metric("Response Rate", f"{response_rate:.1f}%", help="Ответили / Оценка / Сделка от общего числа отправленных")
    with m_col5:
        st.metric("Closed Won (Сделки)", stage_counts["closed_won"], delta=f"Win rate {win_rate:.1f}%")

    st.markdown("---")

    # ==============================================================================
    # Gmail Drafts & Outreach Generator
    # ==============================================================================
    with st.expander("✉️ Генератор персонализированных писем и черновиков Gmail", expanded=False):
        d_contacts_list = fetch_all("SELECT id, brand_name, country, email, decision_maker, cultural_profile, pipeline_status FROM contacts ORDER BY brand_name ASC")
        if not d_contacts_list:
            st.info("В базе нет контактов для аутрича.")
        else:
            d_contact_map = {f"{c['brand_name']} ({c['country'] or 'Global'}) — {c['email'] or 'нет email'}": c["id"] for c in d_contacts_list}
            dg_col1, dg_col2 = st.columns([1, 1], gap="medium")

            with dg_col1:
                sel_dg_label = st.selectbox("1. Выберите бренд для письма:", options=list(d_contact_map.keys()), key="dg_contact_select")
                sel_dg_id = d_contact_map[sel_dg_label]
                dg_contact = next(c for c in d_contacts_list if c["id"] == sel_dg_id)

                template_keys = list(OUTREACH_TEMPLATES.keys())
                template_names = [OUTREACH_TEMPLATES[k]["title"] for k in template_keys]
                sel_tpl_name = st.selectbox("2. Шаблон письма:", options=template_names, key="dg_tpl_select")
                sel_tpl_key = template_keys[template_names.index(sel_tpl_name)]
                chosen_template = OUTREACH_TEMPLATES[sel_tpl_key]

                # Prepare context
                context_dict = {
                    "brand": dg_contact["brand_name"],
                    "name": dg_contact["decision_maker"] or "there",
                    "my_name": st.session_state.get("sender_name", "Тимур"),
                    "portfolio_url": st.session_state.get("portfolio_link", "https://behance.net/gallery/jewelry-retouch"),
                }

                rendered_subj = render_template(chosen_template["subject"], context_dict)
                rendered_body = render_template(chosen_template["body"], context_dict)

                dg_to_email = st.text_input("Email получателя:", value=dg_contact["email"] or "", key="dg_to_email")
                dg_subj_field = st.text_input("Тема письма:", value=rendered_subj, key="dg_subj_field")

            with dg_col2:
                dg_body_field = st.text_area("Текст письма (можно редактировать):", value=rendered_body, height=180, key="dg_body_field")

                b_c1, b_c2, b_c3 = st.columns(3)
                with b_c1:
                    # Direct Gmail Draft Creation
                    if st.button("📨 Создать в Gmail", type="primary", key="create_draft_gmail_btn"):
                        if not dg_to_email.strip():
                            st.error("Укажите email получателя!")
                        else:
                            draft_res = create_gmail_draft(dg_to_email, dg_subj_field, dg_body_field)
                            if draft_res["success"]:
                                st.success("✅ Черновик успешно создан в вашем Gmail!")
                            else:
                                st.warning(f"ℹ️ {draft_res['error']}")
                with b_c2:
                    # Mailto client link
                    mail_subj_enc = urllib.parse.quote(dg_subj_field)
                    mail_body_enc = urllib.parse.quote(dg_body_field)
                    mailto_link = f"mailto:{dg_to_email}?subject={mail_subj_enc}&body={mail_body_enc}"
                    st.link_button("📬 В почтовике", url=mailto_link)
                with b_c3:
                    # Fast Log Touch to CRM
                    if st.button("⚡ Учесть касание", key="log_touch_from_draft_btn"):
                        t_cnt = get_contact_touch_count(sel_dg_id)
                        next_act = calculate_next_action_date(dg_contact["cultural_profile"], date.today(), touch_number=t_cnt + 1)
                        execute_query(
                            """
                            INSERT INTO touches (
                                contact_id, channel, template_type, subject, sent_date,
                                status, next_action_date, notes
                            ) VALUES (?, 'Email', ?, ?, ?, 'sent', ?, ?)
                            """,
                            (
                                sel_dg_id,
                                sel_tpl_key,
                                dg_subj_field,
                                today_str,
                                next_act.isoformat() if next_act else None,
                                f"Отправлено письмо по шаблону '{sel_tpl_name}'",
                            ),
                        )
                        execute_query(
                            "UPDATE contacts SET pipeline_status = 'contacted', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (sel_dg_id,),
                        )
                        st.success(f"Касание зафиксировано! След. действие: {next_act or 'Завершено'}")
                        st.rerun()

    # Mode: Filter for Untouched Base
    col_view_mode, col_quick_log = st.columns([2, 3])
    with col_view_mode:
        only_untouched = st.toggle("🎯 Режим 'Холодная база': показать только без касаний", value=False, key="toggle_untouched")

    if only_untouched:
        st.markdown("### 🧊 Бренды без единого касания (Готовы к первому контакту)")
        if not untouched_contacts:
            st.success("🎉 Все контакты в базе уже получили хотя бы одно касание!")
        else:
            for c in untouched_contacts:
                with st.container(border=True):
                    u_c1, u_c2, u_c3 = st.columns([3, 2, 2])
                    with u_c1:
                        st.markdown(f"**{c['brand_name']}** ({c['country'] or 'Global'})")
                        st.caption(f"Email: {c['email'] or 'нет'} | Сайт: {c['website'] or 'нет'}")
                    with u_c2:
                        p_badge = "🔴 High" if c["priority"] == "high" else ("🟡 Med" if c["priority"] == "medium" else "⚪ Low")
                        st.write(f"Приоритет: {p_badge} | Каденция: `{c['cultural_profile']}`")
                    with u_c3:
                        if st.button("📨 Отправить 1-е касание", key=f"untouched_btn_{c['id']}", type="primary"):
                            st.session_state["quick_touch_target_id"] = c["id"]
                            st.toast(f"Перейдите во вкладку TODAY для отправки касания для {c['brand_name']}")
    else:
        # Kanban Board
        st.markdown("### 📌 Канбан-доска стадий")

        STAGES = [
            ("lead", "📥 Lead", "Лиды"),
            ("contacted", "📨 Contacted", "Отправлено"),
            ("replied", "💬 Replied", "Ответили"),
            ("negotiation", "🤝 Negotiation", "Переговоры"),
            ("closed_won", "🏆 Closed Won", "Сделка"),
            ("closed_lost", "❌ Closed Lost", "Отказ"),
        ]

        stage_keys = [s[0] for s in STAGES]
        cols = st.columns(len(STAGES), gap="small")

        for idx, (st_key, st_title, st_desc) in enumerate(STAGES):
            stage_items = [c for c in all_outreach_contacts if c["pipeline_status"] == st_key]
            with cols[idx]:
                st.markdown(f"**{st_title}** ({len(stage_items)})")
                st.caption(st_desc)

                if not stage_items:
                    st.markdown("<div class='bento-kanban-empty'>Atelier Queue Empty</div>", unsafe_allow_html=True)
                else:
                    for item in stage_items:
                        with st.container(border=True):
                            p_icon = "🔴" if item["priority"] == "high" else ("🟡" if item["priority"] == "medium" else "⚪")
                            st.markdown(f"{p_icon} **{item['brand_name']}**")
                            st.caption(f"🌐 {item['country'] or 'Global'} • `{item['cultural_profile']}`")

                            if item["touches_count"] > 0:
                                st.caption(f"Касаний: **{item['touches_count']}** | Посл.: {item['last_touch_date'] or '—'}")
                                if item["next_action_date"]:
                                    st.caption(f"След.: **{item['next_action_date']}**")
                            else:
                                st.caption("Касаний еще нет")

                            # Stage change dropdown inside card
                            current_stage_idx = stage_keys.index(st_key)
                            new_stage = st.selectbox(
                                "Переместить:",
                                options=stage_keys,
                                index=current_stage_idx,
                                key=f"kanban_select_{item['id']}",
                                label_visibility="collapsed",
                            )

                            if new_stage != st_key:
                                execute_query(
                                    "UPDATE contacts SET pipeline_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                    (new_stage, item["id"]),
                                )
                                st.toast(f"{item['brand_name']} перемещен в {new_stage}!")
                                st.rerun()

# ==============================================================================
# TAB 4: DEALS
# ==============================================================================
with tab_deals:
    st.subheader("💼 Управление сделками и ретейнерами")

    # Fetch all deals with contact details
    deals_full_query = """
        SELECT 
            d.id,
            d.contact_id,
            c.brand_name,
            c.country,
            d.deal_type,
            d.description,
            d.amount_usd,
            d.payment_method,
            d.upwork_contract_url,
            d.status,
            d.created_date,
            d.delivered_date,
            d.paid_date
        FROM deals d
        JOIN contacts c ON d.contact_id = c.id
        ORDER BY d.id DESC
    """
    all_deals_df = get_dataframe(deals_full_query)

    # Fetch retainers
    retainers_full_query = """
        SELECT 
            r.id,
            r.contact_id,
            c.brand_name,
            c.country,
            r.monthly_amount_usd,
            r.images_per_month,
            r.start_month,
            r.status,
            r.next_contract_ping_date,
            r.notes
        FROM retainers r
        JOIN contacts c ON r.contact_id = c.id
        ORDER BY r.id DESC
    """
    all_retainers = fetch_all(retainers_full_query)

    # Top KPI summary cards
    d_in_progress = all_deals_df[all_deals_df["status"] == "in_progress"] if not all_deals_df.empty else pd.DataFrame()
    d_paid = all_deals_df[all_deals_df["status"] == "paid"] if not all_deals_df.empty else pd.DataFrame()
    d_delivered = all_deals_df[all_deals_df["status"] == "delivered"] if not all_deals_df.empty else pd.DataFrame()

    sum_in_progress = d_in_progress["amount_usd"].sum() if not d_in_progress.empty else 0.0
    sum_paid = d_paid["amount_usd"].sum() if not d_paid.empty else 0.0
    active_retainers = [r for r in all_retainers if r["status"] == "active"]
    current_mrr = sum(r["monthly_amount_usd"] for r in active_retainers)

    dk_col1, dk_col2, dk_col3, dk_col4 = st.columns(4)
    with dk_col1:
        st.metric("В работе ($)", f"${sum_in_progress:,.0f}", delta=f"{len(d_in_progress)} сделок")
    with dk_col2:
        st.metric("Сдано / Ждет оплаты", f"{len(d_delivered)} сделок")
    with dk_col3:
        st.metric("Всего оплачено ($)", f"${sum_paid:,.0f}", delta=f"{len(d_paid)} сделок")
    with dk_col4:
        st.metric("Retainer MRR", f"${current_mrr:,.0f}/мес", delta=f"{len(active_retainers)} активных")

    st.markdown("---")

    # Add Deal or Retainer Expander
    with st.expander("➕ Добавить новую сделку или ретейнер", expanded=False):
        form_tab_deal, form_tab_ret = st.tabs(["Новая сделка (Deal)", "Новый ретейнер (Retainer)"])

        contacts_list = fetch_all("SELECT id, brand_name, country FROM contacts ORDER BY brand_name ASC")
        contact_map = {f"{c['brand_name']} ({c['country'] or 'Global'})": c["id"] for c in contacts_list}

        if not contacts_list:
            st.warning("Сначала добавьте контакты во вкладке CONTACTS.")
        else:
            with form_tab_deal:
                with st.form("create_deal_form"):
                    cd1, cd2 = st.columns(2)
                    with cd1:
                        d_contact_label = st.selectbox("Клиент (Бренд) *:", options=list(contact_map.keys()), key="new_deal_contact")
                        d_type = st.selectbox("Тип сделки:", ["one-off", "test", "retainer", "rush_order"], key="new_deal_type")
                        d_amount = st.number_input("Сумма сделки ($ USD) *:", min_value=1.0, value=250.0, step=25.0, key="new_deal_amount")
                        d_method = st.selectbox("Способ оплаты:", ["Upwork", "Direct (Wire/Payoneer)", "Wise", "Crypto", "Other"], key="new_deal_method")
                    with cd2:
                        d_status = st.selectbox("Статус сделки:", ["in_progress", "delivered", "paid", "cancelled"], key="new_deal_status")
                        d_created = st.date_input("Дата создания:", value=date.today(), key="new_deal_created")
                        d_deadline = st.date_input("Дедлайн / Срок сдачи:", value=date.today(), key="new_deal_deadline")
                        d_upwork_url = st.text_input("Upwork Contract URL (опционально):", placeholder="https://www.upwork.com/contracts/~01...", key="new_deal_url")

                    d_desc = st.text_input("Описание проекта:", placeholder="Ретушь 15 артикулов серебряных колец с камнями", key="new_deal_desc")

                    submit_deal = st.form_submit_button("Создать сделку", type="primary")
                    if submit_deal:
                        chosen_cid = contact_map[d_contact_label]
                        paid_dt = date.today().isoformat() if d_status == "paid" else None
                        execute_query(
                            """
                            INSERT INTO deals (
                                contact_id, deal_type, description, amount_usd, payment_method,
                                upwork_contract_url, status, created_date, delivered_date, paid_date
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                chosen_cid,
                                d_type,
                                d_desc.strip(),
                                float(d_amount),
                                d_method,
                                d_upwork_url.strip(),
                                d_status,
                                d_created.isoformat(),
                                d_deadline.isoformat(),
                                paid_dt,
                            ),
                        )
                        # Also update contact pipeline_status to negotiation or closed_won
                        if d_status in ("in_progress", "delivered", "paid"):
                            execute_query(
                                "UPDATE contacts SET pipeline_status = 'closed_won', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                (chosen_cid,),
                            )
                        st.success("Сделка успешно создана!")
                        st.rerun()

            with form_tab_ret:
                with st.form("create_retainer_form"):
                    cr1, cr2 = st.columns(2)
                    with cr1:
                        r_contact_label = st.selectbox("Клиент (Бренд) *:", options=list(contact_map.keys()), key="new_ret_contact")
                        r_amount = st.number_input("Фиксированная сумма ($ USD / месяц) *:", min_value=50.0, value=500.0, step=50.0, key="new_ret_amount")
                        r_images = st.number_input("Лимит фото в месяц:", min_value=1, value=30, step=5, key="new_ret_images")
                    with cr2:
                        r_start = st.text_input("Месяц начала:", value=date.today().strftime("%Y-%m"), key="new_ret_start")
                        r_status = st.selectbox("Статус ретейнера:", ["active", "paused", "completed"], key="new_ret_status")
                        r_ping = st.date_input("Дата контрольного пинга ретейнера:", value=date.today(), key="new_ret_ping")

                    r_notes = st.text_area("Заметки по контракту:", placeholder="Ежемесячный пул фото, сдача до 10 числа каждого месяца", height=70, key="new_ret_notes")

                    submit_ret = st.form_submit_button("Запустить ретейнер", type="primary")
                    if submit_ret:
                        chosen_cid = contact_map[r_contact_label]
                        execute_query(
                            """
                            INSERT INTO retainers (
                                contact_id, monthly_amount_usd, images_per_month, start_month,
                                status, next_contract_ping_date, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                chosen_cid,
                                float(r_amount),
                                int(r_images),
                                r_start.strip(),
                                r_status,
                                r_ping.isoformat(),
                                r_notes.strip(),
                            ),
                        )
                        st.success("Ретейнер активирован!")
                        st.rerun()

    # Deals List & Fast Management
    st.markdown("### 📋 Реестр сделок (Deals)")

    df_col1, df_col2 = st.columns([3, 1])
    with df_col1:
        deal_status_filter = st.selectbox("Фильтр по статусу:", ["Все", "in_progress", "delivered", "paid", "cancelled"], key="deal_filter_status")
    with df_col2:
        st.write("")  # alignment
        st.write(f"Всего сделок: **{len(all_deals_df)}**")

    filtered_deals = all_deals_df
    if deal_status_filter != "Все" and not all_deals_df.empty:
        filtered_deals = all_deals_df[all_deals_df["status"] == deal_status_filter]

    if filtered_deals.empty:
        st.info("Сделок с выбранным статусом не найдено.")
    else:
        st.dataframe(
            filtered_deals[[
                "id", "brand_name", "deal_type", "description", "amount_usd",
                "payment_method", "status", "delivered_date", "paid_date", "upwork_contract_url"
            ]],
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "brand_name": st.column_config.TextColumn("Бренд", width="medium"),
                "deal_type": st.column_config.TextColumn("Тип", width="small"),
                "description": st.column_config.TextColumn("Описание", width="large"),
                "amount_usd": st.column_config.NumberColumn("Сумма USD", format="$%.2f", width="small"),
                "payment_method": st.column_config.TextColumn("Метод", width="small"),
                "status": st.column_config.TextColumn("Статус", width="small"),
                "delivered_date": st.column_config.TextColumn("Срок сдачи", width="small"),
                "paid_date": st.column_config.TextColumn("Дата оплаты", width="small"),
                "upwork_contract_url": st.column_config.LinkColumn("Upwork Contract", width="medium"),
            },
            use_container_width=True,
            hide_index=True,
        )

    # Quick deal status updater
    if not all_deals_df.empty:
        with st.expander("⚡ Быстрое изменение статуса сделки", expanded=False):
            u_deal_map = {f"#{r['id']} — {r['brand_name']} (${r['amount_usd']:.0f}, {r['status']})": r["id"] for _, r in all_deals_df.iterrows()}
            sel_deal_label = st.selectbox("Выберите сделку:", options=list(u_deal_map.keys()), key="sel_deal_for_update")
            sel_deal_id = u_deal_map[sel_deal_label]

            curr_deal = all_deals_df[all_deals_df["id"] == sel_deal_id].iloc[0]
            col_us1, col_us2 = st.columns([3, 1])
            with col_us1:
                next_st_deal = st.selectbox(
                    "Установить новый статус:",
                    options=["in_progress", "delivered", "paid", "cancelled"],
                    index=["in_progress", "delivered", "paid", "cancelled"].index(curr_deal["status"]) if curr_deal["status"] in ["in_progress", "delivered", "paid", "cancelled"] else 0,
                    key="next_st_deal_select",
                )
            with col_us2:
                st.write("")
                st.write("")
                if st.button("Обновить статус", type="primary", key="save_deal_status_btn"):
                    paid_dt = date.today().isoformat() if next_st_deal == "paid" else curr_deal["paid_date"]
                    execute_query(
                        "UPDATE deals SET status = ?, paid_date = ? WHERE id = ?",
                        (next_st_deal, paid_dt, sel_deal_id),
                    )
                    st.toast(f"Статус сделки #{sel_deal_id} изменен на {next_st_deal}!")
                    st.rerun()

    st.markdown("---")

    # ==============================================================================
    # Retainers Management Section
    # ==============================================================================
    st.markdown("### 🔄 Долгосрочные ретейнеры (Monthly Retainers)")
    if not all_retainers:
        st.info("Ретейнеры пока не зафиксированы. Настройте долгосрочный контракт через форму выше.")
    else:
        r_cols = st.columns(min(3, len(all_retainers)), gap="medium")
        for idx, ret in enumerate(all_retainers):
            with r_cols[idx % len(r_cols)]:
                with st.container(border=True):
                    is_active = ret["status"] == "active"
                    st_badge = "🟢 Активен" if is_active else f"⚪ {ret['status']}"
                    st.markdown(f"**{ret['brand_name']}** ({ret['country'] or 'Global'}) — {st_badge}")
                    st.metric("Ежемесячно", f"${ret['monthly_amount_usd']:.0f}/мес", delta=f"{ret['images_per_month']} фото")
                    st.caption(f"Старт: {ret['start_month']} | Пинг: **{ret['next_contract_ping_date']}**")
                    if ret["notes"]:
                        st.caption(f"Условия: {ret['notes']}")

                    if st.button("🔔 Пинг отправлен (+1 мес)", key=f"ping_ret_{ret['id']}"):
                        # Bump next ping by 30 days
                        try:
                            curr_dt = datetime.strptime(ret["next_contract_ping_date"], "%Y-%m-%d").date()
                            next_ping = (curr_dt + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
                        except Exception:
                            next_ping = (date.today() + pd.Timedelta(days=30)).strftime("%Y-%m-%d")

                        execute_query(
                            "UPDATE retainers SET next_contract_ping_date = ? WHERE id = ?",
                            (next_ping, ret["id"]),
                        )
                        st.toast(f"Дата контрольного пинга перенесена на {next_ping}!")
                        st.rerun()

# ==============================================================================
# TAB 5: MONEY
# ==============================================================================
with tab_money:
    st.subheader("💰 Финансы, Платежи и Налоги ФОП")

    # Fetch all payments with deal and contact metadata
    payments_query = """
        SELECT 
            p.id,
            p.deal_id,
            c.brand_name,
            d.description AS deal_desc,
            d.payment_method,
            p.gross_usd,
            p.platform_fee_percent,
            p.platform_fee_usd,
            p.withdrawal_fee,
            p.net_usd,
            p.usd_uah_rate,
            p.net_uah,
            p.tax_rate,
            p.tax_reserved_uah,
            p.date_received,
            p.date_withdrawn,
            p.declaration_month
        FROM payments p
        JOIN deals d ON p.deal_id = d.id
        JOIN contacts c ON d.contact_id = c.id
        ORDER BY p.date_withdrawn DESC, p.id DESC
    """
    all_payments_df = get_dataframe(payments_query)

    # Month selector for declaration
    available_months = ["Все месяцы"]
    if not all_payments_df.empty:
        distinct_months = sorted(
            [m for m in all_payments_df["declaration_month"].dropna().unique() if m],
            reverse=True,
        )
        available_months.extend(distinct_months)
    current_month_str = date.today().strftime("%Y-%m")
    if current_month_str not in available_months:
        available_months.insert(1, current_month_str)

    sel_m_col1, sel_m_col2 = st.columns([2, 2])
    with sel_m_col1:
        chosen_month = st.selectbox("Отчетный месяц декларации:", options=available_months, index=0, key="money_chosen_month")

    # Filtered payments
    if chosen_month == "Все месяцы":
        period_payments_df = all_payments_df
    else:
        period_payments_df = all_payments_df[all_payments_df["declaration_month"] == chosen_month] if not all_payments_df.empty else pd.DataFrame()

    # Period KPIs
    tot_gross = period_payments_df["gross_usd"].sum() if not period_payments_df.empty else 0.0
    tot_fees = (period_payments_df["platform_fee_usd"].sum() + period_payments_df["withdrawal_fee"].sum()) if not period_payments_df.empty else 0.0
    tot_net_usd = period_payments_df["net_usd"].sum() if not period_payments_df.empty else 0.0
    tot_net_uah = period_payments_df["net_uah"].sum() if not period_payments_df.empty else 0.0
    tot_tax_uah = period_payments_df["tax_reserved_uah"].sum() if not period_payments_df.empty else 0.0

    kpi_m1, kpi_m2, kpi_m3, kpi_m4, kpi_m5 = st.columns(5)
    with kpi_m1:
        st.metric("Gross USD (Вал)", f"${tot_gross:,.2f}")
    with kpi_m2:
        st.metric("Комиссии (Fees)", f"${tot_fees:,.2f}")
    with kpi_m3:
        st.metric("Net USD (Чистыми)", f"${tot_net_usd:,.2f}")
    with kpi_m4:
        st.metric("Net UAH (Гривна)", f"₴{tot_net_uah:,.2f}")
    with kpi_m5:
        st.metric("Налог (19.5%)", f"₴{tot_tax_uah:,.2f}", delta="18% НДФЛ + 1.5% ВС", delta_color="inverse")

    st.markdown("---")

    # Payment Logging Form with Live Auto-Calculation
    with st.expander("➕ Внести полученный платеж (с авто-расчетом налогов)", expanded=False):
        # Deals eligible for payment
        eligible_deals = fetch_all(
            """
            SELECT d.id, d.amount_usd, d.description, d.payment_method, c.brand_name
            FROM deals d
            JOIN contacts c ON d.contact_id = c.id
            ORDER BY d.id DESC
            """
        )

        if not eligible_deals:
            st.warning("В базе нет сделок. Создайте сделку во вкладке DEALS.")
        else:
            deal_pay_options = {
                f"#{d['id']} — {d['brand_name']}: {d['description'] or 'Ретушь'} (${d['amount_usd']:.0f}) [{d['payment_method']}]": d["id"]
                for d in eligible_deals
            }
            sel_pay_deal_label = st.selectbox("1. Выберите оплачиваемую сделку *:", options=list(deal_pay_options.keys()), key="pay_deal_select")
            sel_pay_deal_id = deal_pay_options[sel_pay_deal_label]

            selected_deal_row = next(d for d in eligible_deals if d["id"] == sel_pay_deal_id)
            is_upwork = "upwork" in (selected_deal_row["payment_method"] or "").lower()

            f_pcol1, f_pcol2, f_pcol3 = st.columns(3)
            with f_pcol1:
                p_gross = st.number_input(
                    "Сумма платежа ($ Gross USD) *:",
                    min_value=1.0,
                    value=float(selected_deal_row["amount_usd"]),
                    step=25.0,
                    key="pay_gross_in",
                )
                p_fee_pct = st.number_input(
                    "Комиссия платформы (%):",
                    min_value=0.0,
                    max_value=50.0,
                    value=10.0 if is_upwork else 0.0,
                    step=1.0,
                    key="pay_fee_pct_in",
                )
            with f_pcol2:
                p_with_fee = st.number_input(
                    "Комиссия за вывод ($ withdrawal):",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key="pay_with_fee_in",
                )
                p_rate = st.number_input(
                    "Курс USD / UAH:",
                    min_value=1.0,
                    value=41.20,
                    step=0.10,
                    key="pay_rate_in",
                )
            with f_pcol3:
                p_rec_date = st.date_input("Дата получения на счет:", value=date.today(), key="pay_rec_date")
                p_with_date = st.date_input("Дата вывода:", value=date.today(), key="pay_with_date")
                p_decl_month = st.text_input("Отчетный месяц (YYYY-MM):", value=date.today().strftime("%Y-%m"), key="pay_month_in")

            # Live calculation preview
            from logic import calculate_payment_breakdown
            calc_res = calculate_payment_breakdown(
                gross_usd=p_gross,
                platform_fee_percent=p_fee_pct,
                withdrawal_fee=p_with_fee,
                usd_uah_rate=p_rate,
                tax_rate=0.195,
            )

            st.info(
                f"🧮 **Авто-расчет:** Комиссия платформы: **${calc_res['platform_fee_usd']:.2f}** | "
                f"Чистыми USD: **${calc_res['net_usd']:.2f}** | "
                f"Чистыми UAH: **₴{calc_res['net_uah']:,.2f}** | "
                f"Резерв налога (19.5%): **₴{calc_res['tax_reserved_uah']:,.2f}**"
            )

            if st.button("💾 Зафиксировать платеж и провести", type="primary", key="save_payment_btn"):
                execute_query(
                    """
                    INSERT INTO payments (
                        deal_id, gross_usd, platform_fee_percent, platform_fee_usd,
                        withdrawal_fee, net_usd, usd_uah_rate, net_uah, tax_rate,
                        tax_reserved_uah, date_received, date_withdrawn, declaration_month
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sel_pay_deal_id,
                        calc_res["gross_usd"],
                        calc_res["platform_fee_percent"],
                        calc_res["platform_fee_usd"],
                        calc_res["withdrawal_fee"],
                        calc_res["net_usd"],
                        calc_res["usd_uah_rate"],
                        calc_res["net_uah"],
                        calc_res["tax_rate"],
                        calc_res["tax_reserved_uah"],
                        p_rec_date.isoformat(),
                        p_with_date.isoformat(),
                        p_decl_month.strip(),
                    ),
                )

                # Mark deal as paid
                execute_query(
                    "UPDATE deals SET status = 'paid', paid_date = ? WHERE id = ?",
                    (p_rec_date.isoformat(), sel_pay_deal_id),
                )

                st.success("Платеж успешно внесен в реестр и сделка помечена оплаченной!")
                st.rerun()

    # Tax Declaration Table & CSV Export
    st.markdown("### 📑 Реестр поступлений для налоговой декларации")

    if period_payments_df.empty:
        st.info(f"За период '{chosen_month}' платежей не зарегистрировано.")
    else:
        disp_df = period_payments_df[[
            "id", "declaration_month", "date_withdrawn", "brand_name", "deal_desc",
            "payment_method", "gross_usd", "platform_fee_usd", "net_usd",
            "usd_uah_rate", "net_uah", "tax_reserved_uah"
        ]].copy()

        # CSV Download button
        p_col_cnt, p_col_csv = st.columns([4, 1])
        with p_col_cnt:
            st.caption(f"Показано транзакций: **{len(disp_df)}** | Суммарный налог к уплате: **₴{tot_tax_uah:,.2f}**")
        with p_col_csv:
            csv_pay_buf = io.StringIO()
            disp_df.to_csv(csv_pay_buf, index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Скачать реестр (CSV)",
                data=csv_pay_buf.getvalue(),
                file_name=f"tax_declaration_{chosen_month}.csv",
                mime="text/csv",
                key="download_tax_csv_btn",
            )

        st.dataframe(
            disp_df,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "declaration_month": st.column_config.TextColumn("Месяц", width="small"),
                "date_withdrawn": st.column_config.TextColumn("Дата вывода", width="small"),
                "brand_name": st.column_config.TextColumn("Бренд", width="medium"),
                "deal_desc": st.column_config.TextColumn("Сделка", width="medium"),
                "payment_method": st.column_config.TextColumn("Платформа", width="small"),
                "gross_usd": st.column_config.NumberColumn("Вал USD", format="$%.2f", width="small"),
                "platform_fee_usd": st.column_config.NumberColumn("Комиссия USD", format="$%.2f", width="small"),
                "net_usd": st.column_config.NumberColumn("Net USD", format="$%.2f", width="small"),
                "usd_uah_rate": st.column_config.NumberColumn("Курс UAH", format="%.2f", width="small"),
                "net_uah": st.column_config.NumberColumn("Net UAH", format="₴%.2f", width="small"),
                "tax_reserved_uah": st.column_config.NumberColumn("Налог 19.5% UAH", format="₴%.2f", width="small"),
            },
            use_container_width=True,
            hide_index=True,
        )

# ==============================================================================
# TAB 6: DASHBOARD
# ==============================================================================
with tab_dashboard:
    st.subheader("📊 Аналитика бизнеса, MRR и Здоровье базы")

    # Fetch aggregated metrics from DB
    d_contacts = get_dataframe("SELECT * FROM contacts")
    d_deals = get_dataframe("SELECT * FROM deals")
    d_payments = get_dataframe("SELECT * FROM payments")
    d_retainers = get_dataframe("SELECT * FROM retainers WHERE status = 'active'")

    # 1. Target & Revenue Progress (Цели)
    st.markdown("### 🎯 Финансовая цель на месяц")
    current_mo_str = date.today().strftime("%Y-%m")

    # Monthly revenue fact
    curr_mo_payments = d_payments[d_payments["declaration_month"] == current_mo_str] if not d_payments.empty else pd.DataFrame()
    curr_mo_paid_usd = curr_mo_payments["net_usd"].sum() if not curr_mo_payments.empty else 0.0

    # Active retainers MRR
    active_mrr = d_retainers["monthly_amount_usd"].sum() if not d_retainers.empty else 0.0

    col_g1, col_g2 = st.columns([1, 3])
    with col_g1:
        if "monthly_revenue_goal" not in st.session_state:
            st.session_state["monthly_revenue_goal"] = 2500.0
        goal_val = st.number_input(
            "Цель чистой выручки ($):",
            min_value=500.0,
            value=st.session_state["monthly_revenue_goal"],
            step=250.0,
            key="input_goal_val",
        )
        st.session_state["monthly_revenue_goal"] = goal_val

    with col_g2:
        total_mo_forecast = curr_mo_paid_usd + active_mrr
        pct_achieved = min(1.0, total_mo_forecast / goal_val) if goal_val > 0 else 0.0
        st.progress(pct_achieved, text=f"Выполнено: ${total_mo_forecast:,.0f} из ${goal_val:,.0f} ({pct_achieved * 100:.1f}%)")

        rem_to_goal = max(0.0, goal_val - total_mo_forecast)
        st.caption(
            f"Фактически получено в {current_mo_str}: **${curr_mo_paid_usd:,.0f}** | "
            f"Гарантированный MRR ретейнеров: **${active_mrr:,.0f}** | "
            f"Осталось до цели: **${rem_to_goal:,.0f}**"
        )

    st.markdown("---")

    # 2. Retainers & MRR Health
    st.markdown("### 🔄 Метрики подписок (Retainer & MRR)")
    r_kpi1, r_kpi2, r_kpi3, r_kpi4 = st.columns(4)
    with r_kpi1:
        st.metric("Текущий MRR", f"${active_mrr:,.0f}/мес", delta=f"{len(d_retainers)} клиентов")
    with r_kpi2:
        annual_run_rate = active_mrr * 12.0
        st.metric("Годовой прогноз (ARR)", f"${annual_run_rate:,.0f}/год")
    with r_kpi3:
        total_ret_photos = d_retainers["images_per_month"].sum() if not d_retainers.empty else 0
        st.metric("Фото в месяц (пул)", f"{total_ret_photos} шт.")
    with r_kpi4:
        avg_per_photo = (active_mrr / total_ret_photos) if total_ret_photos > 0 else 0.0
        st.metric("Средний чек за фото", f"${avg_per_photo:.2f}/фото" if avg_per_photo > 0 else "—")

    st.markdown("---")

    # 3. Funnel Conversion
    st.markdown("### 🌪️ Воронка продаж и конверсии")
    if not d_contacts.empty:
        total_c = len(d_contacts)
        st_lead = len(d_contacts[d_contacts["pipeline_status"] == "lead"])
        st_contacted = len(d_contacts[d_contacts["pipeline_status"] == "contacted"])
        st_replied = len(d_contacts[d_contacts["pipeline_status"] == "replied"])
        st_neg = len(d_contacts[d_contacts["pipeline_status"] == "negotiation"])
        st_won = len(d_contacts[d_contacts["pipeline_status"] == "closed_won"])
        st_lost = len(d_contacts[d_contacts["pipeline_status"] == "closed_lost"])

        fn_c1, fn_c2, fn_c3, fn_c4, fn_c5 = st.columns(5)
        with fn_c1:
            st.metric("1. Лиды (Leads)", total_c)
        with fn_c2:
            outreach_done = total_c - st_lead
            outreach_pct = (outreach_done / total_c * 100) if total_c > 0 else 0
            st.metric("2. В контакте", outreach_done, delta=f"{outreach_pct:.0f}% базы")
        with fn_c3:
            replied_pool = st_replied + st_neg + st_won
            rep_pct = (replied_pool / outreach_done * 100) if outreach_done > 0 else 0
            st.metric("3. Ответили (Диалог)", replied_pool, delta=f"{rep_pct:.1f}% отклик")
        with fn_c4:
            deal_pool = st_neg + st_won
            st.metric("4. КП / Переговоры", deal_pool)
        with fn_c5:
            win_pct = (st_won / outreach_done * 100) if outreach_done > 0 else 0
            st.metric("5. Сделки (Won)", st_won, delta=f"{win_pct:.1f}% конверсия")

    st.markdown("---")

    # 4. Database Health
    st.markdown("### 🏥 Здоровье базы контактов")
    if not d_contacts.empty:
        h_col1, h_col2, h_col3 = st.columns(3)

        with h_col1:
            st.markdown("##### Сегментация по каденциям (культура)")
            culture_counts = d_contacts["cultural_profile"].value_counts().to_dict()
            for prof, cnt in culture_counts.items():
                st.write(f"- **{prof.capitalize()}**: {cnt} брендов ({(cnt / total_c * 100):.0f}%)")

        with h_col2:
            st.markdown("##### Приоритеты ретуши")
            priority_counts = d_contacts["priority"].value_counts().to_dict()
            for prio, cnt in priority_counts.items():
                p_icon = "🔴" if prio == "high" else ("🟡" if prio == "medium" else "⚪")
                st.write(f"- {p_icon} **{prio.capitalize()}**: {cnt} брендов")

        with h_col3:
            st.markdown("##### Качество данных")
            valid_emails = len(d_contacts[d_contacts["email_status"] == "valid"])
            has_website = len(d_contacts[d_contacts["website"].notna() & (d_contacts["website"] != "")])
            has_insta = len(d_contacts[d_contacts["instagram"].notna() & (d_contacts["instagram"] != "")])

            st.write(f"✅ Валидных Email: **{valid_emails}** ({(valid_emails / total_c * 100):.0f}%)")
            st.write(f"🌐 Сайтов в базе: **{has_website}** ({(has_website / total_c * 100):.0f}%)")
            st.write(f"📸 Instagram аккаунтов: **{has_insta}** ({(has_insta / total_c * 100):.0f}%)")
