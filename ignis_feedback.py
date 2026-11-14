"""Public contact and contributions channel for Team IGNIS.

The app does not store contributions in Streamlit or publish them automatically.
Publishing requires the person to confirm the Issue on GitHub.
"""
from urllib.parse import urlencode
import requests
import streamlit as st

REPO = "sarapcoffee/ignis-uy-historico"
REPO_URL = f"https://github.com/{REPO}"
ISSUES_URL = f"{REPO_URL}/issues"


@st.cache_data(ttl=300, show_spinner=False)
def estado_issues():
    try:
        response = requests.get(
            f"https://api.github.com/repos/{REPO}",
            headers={"Accept": "application/vnd.github+json"},
            timeout=(3, 5),
        )
        response.raise_for_status()
        flag = response.json().get("has_issues")
        return flag if isinstance(flag, bool) else None
    except (requests.RequestException, ValueError):
        return None


def preparar_aporte(categoria: str, titulo: str, descripcion: str, referencia: str = ""):
    """Builds the URL and draft without sending anything or handling credentials."""
    titulo = " ".join(str(titulo).split())[:110]
    descripcion = str(descripcion).strip()[:1500]
    referencia = str(referencia or "").strip()[:350]
    mensaje = (
        "## Contribution type\n" + categoria +
        "\n\n## Question or proposal\n" + descripcion +
        "\n\n## Source or reference (optional)\n" +
        (referencia or "Not provided") +
        "\n\n---\nPrepared from IGNIS UY. "
        "Contributions remain pending review; "
        "they do not confirm fires or automatically validate FIRMS data."
    )
    parametros = urlencode({
        "title": f"[Team IGNIS] {categoria}: {titulo}",
        "body": mensaje,
    })
    return f"{ISSUES_URL}/new?{parametros}", mensaje


def mostrar_contacto_team():
    st.markdown(
        '<div class="ignis-ui-kicker">Community · Open research</div>',
        unsafe_allow_html=True,
    )
    st.title("Questions and contributions to Team IGNIS")
    st.write(
        "Share suggestions, questions, bugs or documentary references. "
        "News and testimonies are contributions pending review, "
        "not automatic verifications of thermal detections."
    )
    issues = estado_issues()
    if issues is False:
        st.warning(
            "GitHub Issues is disabled. To receive contributions, "
            "the team must enable it on GitHub → Settings → General "
            "→ Features → Issues. In the meantime you can prepare a draft."
        )
    elif issues is None:
        st.info(
            "It was not possible to verify whether GitHub Issues is active. "
            "The draft can be downloaded, without claiming it was sent."
        )
    else:
        st.success(
            "GitHub Issues is available: you can prepare your contribution "
            "and publish it from your GitHub account."
        )

    st.caption(
        "Published Issues are public. Do not include passwords, API keys, "
        "phone numbers, addresses or personal information about third parties. "
        "A GitHub account is required to publish."
    )
    with st.form("team_ignis_aporte", clear_on_submit=False):
        tipo = st.selectbox(
            "Contribution type",
            [
                "Question about the data",
                "Documentary source or news",
                "Report a bug",
                "Improvement suggestion",
                "Scientific or technical collaboration",
            ],
        )
        asunto = st.text_input(
            "Short title", max_chars=110,
            placeholder="E.g.: Fire source in Durazno, January 2022",
        )
        detalle = st.text_area(
            "Question or proposal", max_chars=1500, height=180,
            placeholder="Describe the dates, coordinates, evidence or the bug you found.",
        )
        referencia = st.text_input(
            "Reference link (optional)", max_chars=350,
            placeholder="https://...",
        )
        confirmado = st.checkbox(
            "I understand the Issue will be public and that it has not been sent yet."
        )
        preparar = st.form_submit_button(
            "Prepare for GitHub", type="primary", use_container_width=True
        )

    if preparar:
        if len(asunto.strip()) < 8:
            st.error("Write a title of at least 8 characters.")
        elif len(detalle.strip()) < 20:
            st.error("Explain the contribution with at least 20 characters.")
        elif referencia.strip() and not referencia.strip().startswith(("https://", "http://")):
            st.error("The reference must start with https:// or http://.")
        elif not confirmado:
            st.error("Confirm that you understand the publication is public.")
        else:
            url, borrador = preparar_aporte(tipo, asunto, detalle, referencia)
            st.session_state["ignis_team_draft"] = {"url": url, "body": borrador}

    draft = st.session_state.get("ignis_team_draft")
    if draft:
        st.subheader("Draft prepared")
        st.caption("It has not been sent yet. Download it or, if Issues is active, publish it.")
        with st.expander("View the content"):
            st.code(draft["body"], language="markdown")
        st.download_button(
            "Download draft (.md)", data=draft["body"].encode("utf-8"),
            file_name="team_ignis_contribution.md", mime="text/markdown",
            use_container_width=True, key="team_draft_download",
        )
        if issues is True:
            st.link_button(
                "Continue and publish on GitHub Issues",
                draft["url"], type="primary", use_container_width=True,
            )
            st.caption(
                "GitHub requires signing in and confirming “Submit new issue”. "
                "IGNIS cannot check here whether you published it."
            )
        else:
            st.info(
                "The publish link will appear once GitHub Issues "
                "is enabled and its status can be checked."
            )

    st.divider()
    st.link_button("View IGNIS UY repository", REPO_URL, use_container_width=True)
    st.caption(
        "We do not guarantee a reply or the inclusion of sources without review."
    )
