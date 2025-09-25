import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components
from datetime import datetime
import os
import ast
from supabase_client import supabase
import json

# === CONFIGURATION ===
st.set_page_config(page_title="Entraînement Lois du Jeu", page_icon="⚽", layout="centered")
st.title("📘 Entraînement aux Lois du Jeu - FAR")

comptes_df = pd.read_csv("comptes_arbitres.csv", dtype=str)

if "utilisateur" not in st.session_state:
    with st.form("login"):
        login = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

    if submitted:
        user = comptes_df[(comptes_df["Login"] == login) & (comptes_df["Password"] == password)]
        if not user.empty:
            st.session_state["utilisateur"] = user.iloc[0].to_dict()
            st.success(f"Bienvenue {user.iloc[0]['Prénom']} !")
            st.rerun()
        else:
            st.error("Identifiants incorrects")

if "utilisateur" in st.session_state:
    st.sidebar.success(f"Connecté en tant que {st.session_state['utilisateur']['Prénom']}")
    if st.sidebar.button("Se déconnecter"):
        del st.session_state["utilisateur"]
        st.rerun()

    if st.session_state["utilisateur"]["Login"] == "admin":
        st.subheader("📊 Suivi global de la participation")

        response = supabase.table("historique_sessions").select("*").execute()
        histo = pd.DataFrame(response.data)


        if histo.empty:
            st.warning("⚠️ Aucune donnée trouvée dans Supabase.")
        else:
            # Ajout des colonnes utiles
            stats = histo.groupby("login").agg({
                "date": "count",
                "nb_questions": "sum",
            }).rename(columns={
                "date": "Sessions",
                "nb_questions": "Questions générées"
            })
            stats["Moyenne Q/session"] = (stats["Questions générées"] / stats["Sessions"]).round(2)

            # Dernière session
            last_sessions = histo.groupby("login")["date"].max().rename("Dernière session")
            stats = stats.join(last_sessions)

            st.dataframe(stats.sort_values("Sessions", ascending=False))

        # Vue par arbitre
        st.markdown("## 🔎 Détail par arbitre")

        comptes_df = pd.read_csv("comptes_arbitres.csv", dtype=str)
        logins = comptes_df[comptes_df["Login"] != "admin"]["Login"].tolist()
        login_selectionne = st.selectbox("Sélectionnez un arbitre :", logins)
        st.write("Colonnes disponibles :", histo.columns.tolist())      
        histo_user = histo[histo["login"] == login_selectionne]
        compte_user = comptes_df[comptes_df["Login"] == login_selectionne].iloc[0]

        st.markdown(f"### 👤 {compte_user['Prénom']} {compte_user['Nom']}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Sessions", len(histo_user))
        col2.metric("Questions générées", histo_user["nb_questions"].sum())
        col3.metric("Dernière session", histo_user["date"].max())

        st.markdown("#### 📄 Sessions récentes")
        st.dataframe(histo_user.sort_values("date", ascending=False).reset_index(drop=True))

        # Détails graphiques
        if "details_questions" in histo_user.columns and not histo_user["details_questions"].dropna().empty:
            details_exploded = (
                histo_user["details_questions"]
                .dropna()
                .apply(lambda x: json.loads(x) if isinstance(x, str) else x)
                .explode()
            )
            questions_details_df = pd.DataFrame(details_exploded.tolist())

            if not questions_details_df.empty:
                st.markdown("#### 📚 Lois les plus travaillées")
                st.bar_chart(questions_details_df["Loi"].value_counts())

                colf1, colf2 = st.columns(2)
                colf1.markdown("#### 📝 Formats les plus fréquents")
                colf1.bar_chart(questions_details_df["Format"].value_counts())

                colf2.markdown("#### 🎯 Niveaux travaillés")
                colf2.bar_chart(questions_details_df["Niveau"].value_counts())




    if st.session_state["utilisateur"]["Login"] != "admin":
        # === TABLEAU DE BORD PERSONNEL ===
        st.subheader("📊 Mon tableau de bord")

        # Lecture de l'historique complet depuis Supabase
        response = supabase.table("historique_sessions").select("*").execute()
        st.write("🔍 Réponse Supabase :", response)  # debug
        histo = pd.DataFrame(response.data)

        if histo.empty:
            st.warning("⚠️ Aucune donnée trouvée dans la table Supabase `historique_sessions`.")
        else:
            st.write("Colonnes disponibles après normalisation :", histo.columns.tolist())

            user_login = st.session_state["utilisateur"]["Login"]

            if "login" not in histo.columns:
                st.error("❌ La colonne 'login' est absente de la table Supabase. Vérifie le schéma.")
            else:
                histo_user = histo[histo["login"] == user_login]

                if histo_user.empty:
                    st.info("ℹ️ Aucune session enregistrée pour cet utilisateur.")
                else:
                    # === METRICS GLOBALES ===
                    col1, col2 = st.columns(2)
                    col1.metric("📅 Sessions effectuées", len(histo_user))
                    col2.metric("❓ Questions générées", histo_user["nb_questions"].sum())

                    # Conversion de 'DetailsQuestions' si dispo
                    if "details_questions" in histo_user.columns:
                        details_exploded = (
                            histo_user["details_questions"]
                            .dropna()
                            .apply(lambda x: json.loads(x) if isinstance(x, str) else x)
                            .explode()
                        )
                        questions_details_df = pd.DataFrame(details_exploded.tolist())

                        if not questions_details_df.empty:
                            lois_counts = questions_details_df["Loi"].value_counts().head(5)
                            st.markdown("### 📚 Lois les plus travaillées")
                            st.bar_chart(lois_counts)

                            formats_counts = questions_details_df["Format"].value_counts()
                            col3, col4 = st.columns(2)
                            col3.markdown("### 📝 Formats")
                            col3.bar_chart(formats_counts)

                            niveaux_counts = questions_details_df["Niveau"].value_counts()
                            col4.markdown("### 🎯 Niveaux")
                            col4.bar_chart(niveaux_counts)


    # === CHARGEMENT DES QUESTIONS ===
    @st.cache_data
    def load_questions():
        df = pd.read_excel("questions_lois_du_jeu.xlsx")
        return df

    questions_df = load_questions()

    # Nettoyage & préparation
    questions_df["Loi"] = questions_df["Loi"].astype(str)
    questions_df["Format"] = questions_df["Format"].astype(str)
    questions_df["Type"] = questions_df["Type"].astype(str)
    questions_df["Niveau"] = questions_df["Niveau"].astype(str)


    # === FILTRES EN MODE TUILES ===
    st.header("🎛️ Paramètres d'entraînement")

    # === LOIS DU JEU ===
    st.subheader("📚 Lois à travailler")

    # Liste réelle des valeurs de lois
    lois_connues = [str(i) for i in range(1, 18)] + ["Définition", "Autre"]

    # Libellé affiché = clé réelle → label
    loi_labels = {
        "Définition": "Définitions",
        "Autre": "Autre",
        **{str(i): f"Loi {i}" for i in range(1, 18)}
    }

    cols_lois = st.columns(5)
    selected_lois = []

    for idx, loi in enumerate(lois_connues):
        label = loi_labels[loi]
        with cols_lois[idx % 5]:
            if st.toggle(label, key=f"loi_{loi}", value=False):
                selected_lois.append(loi)

    # Fonctions pour tout cocher / décocher
    def select_all_lois():
        for loi in lois_connues:
            st.session_state[f"loi_{loi}"] = True

    def deselect_all_lois():
        for loi in lois_connues:
            st.session_state[f"loi_{loi}"] = False

    col_a, col_b = st.columns(2)
    col_a.button("✅ Tout sélectionner", on_click=select_all_lois)
    col_b.button("❌ Tout désélectionner", on_click=deselect_all_lois)


    # === FORMAT ===
    st.subheader("📝 Format de question")
    formats = sorted(questions_df["Format"].dropna().unique().tolist())
    cols_fmt = st.columns(len(formats))
    selected_formats = []

    for idx, fmt in enumerate(formats):
        with cols_fmt[idx % len(cols_fmt)]:
            if st.toggle(fmt, key=f"format_{fmt}", value=True):
                selected_formats.append(fmt)


    # === TYPE ===
    st.subheader("📂 Type de question")
    types = sorted(questions_df["Type"].dropna().unique().tolist())
    cols_types = st.columns(len(types))
    selected_types = []

    for idx, typ in enumerate(types):
        with cols_types[idx % len(cols_types)]:
            if st.toggle(typ, key=f"type_{typ}", value=True):
                selected_types.append(typ)


    # === NIVEAU ===
    st.subheader("🎯 Niveau")
    ordre_niveaux = ["Facile", "Moyen", "Difficile"]
    niveaux_disponibles = questions_df["Niveau"].dropna().unique().tolist()
    niveaux = [n for n in ordre_niveaux if n in niveaux_disponibles]
    cols_niv = st.columns(len(niveaux))
    selected_niveaux = []

    for idx, niv in enumerate(niveaux):
        with cols_niv[idx % len(niveaux)]:
            if st.toggle(niv, key=f"niveau_{niv}", value=True):
                selected_niveaux.append(niv)


    # === NOMBRE DE QUESTIONS ===
    st.subheader("🎲 Nombre de questions à afficher")
    nb_questions = st.radio("Sélectionnez :", [1, 3, 5, 10], horizontal=True)

    # === FILTRAGE FINAL ===
    filtered_df = questions_df[
        (questions_df["Loi"].isin(selected_lois)) &
        (questions_df["Format"].isin(selected_formats)) &
        (questions_df["Type"].isin(selected_types)) &
        (questions_df["Niveau"].isin(selected_niveaux))
    ]

    def enregistrer_session(user_login, questions_df_tirees):
        questions_infos = questions_df_tirees[["Loi", "Format", "Type", "Niveau"]].astype(str).to_dict(orient="records")

        data = {
            "login": user_login,
            "date": datetime.now().isoformat(),
            "nb_questions": len(questions_df_tirees),   # ✅ avec underscore
            "details_questions": json.dumps(questions_infos, ensure_ascii=False)  # ✅ avec underscore
        }

        st.write("🔍 Données envoyées à Supabase :", data)

        try:
            res = supabase.table("historique_sessions").insert(data).execute()
            st.success("✅ Session enregistrée dans Supabase")
            st.write(res)
        except Exception as e:
            st.error(f"❌ Erreur lors de l'insertion Supabase : {e}")






    # === TIRAGE ALÉATOIRE ===
    if st.button("🚀 Générer les questions"):
        if filtered_df.empty:
            st.warning("Aucune question ne correspond aux filtres sélectionnés.")
        else:
            st.session_state["questions_tirees"] = filtered_df.sample(min(nb_questions, len(filtered_df))).reset_index(drop=True)
            user_login = st.session_state["utilisateur"]["Login"]
            enregistrer_session(user_login, st.session_state["questions_tirees"])
            st.rerun()



    # === ESPACE VISUEL DE TRANSITION ===
    st.markdown(" ")
    st.markdown("---")
    st.markdown(" ")

    # === AFFICHAGE DES QUESTIONS ===
    if "questions_tirees" in st.session_state:
        st.header("📋 Questions tirées")

        for i, row in st.session_state["questions_tirees"].iterrows():
            st.markdown(f"### ❓ Question {i+1}")

            # 🏷️ Éléments contextuels
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.markdown(f"<div style='background-color:#d3d3d3; padding:5px; border-radius:5px; text-align:center;'>ID : {row['ID']}</div>", unsafe_allow_html=True)
            col2.markdown(f"<div style='background-color:#f0ad4e; padding:5px; border-radius:5px; text-align:center;'>Loi : {row['Loi']}</div>", unsafe_allow_html=True)
            col3.markdown(f"<div style='background-color:#5bc0de; padding:5px; border-radius:5px; text-align:center;'>Type : {row['Type']}</div>", unsafe_allow_html=True)
            col4.markdown(f"<div style='background-color:#5cb85c; padding:5px; border-radius:5px; text-align:center;'>Niveau : {row['Niveau']}</div>", unsafe_allow_html=True)
            col5.markdown(f"<div style='background-color:#d9534f; padding:5px; border-radius:5px; text-align:center;'>Source : {row['Source']}</div>", unsafe_allow_html=True)

            # 🧾 Question
            st.markdown(f"**{row['Question']}**")

            # ✅ Si QCM → affichage boutons cliquables
            if "qcm" in row["Format"].lower() and pd.notna(row["Propositions"]):
                propositions = [p.strip() for p in str(row["Propositions"]).split("\n") if p.strip()]
                selected_prop = st.radio("Choisissez votre réponse :", propositions, key=f"qcm_{i}")
            else:
                st.text_area("Votre réponse :", key=f"reponse_{i}")

            # 👁️ Affichage réponse
            if st.button(f"👁️ Voir la réponse (Question {i+1})", key=f"btn_{i}"):
                reponse_formatee = str(row["Réponse attendue"]).replace("\n", "  \n")  # Pour retour à la ligne
                st.success(f"**Réponse attendue :**  \n{reponse_formatee}")
