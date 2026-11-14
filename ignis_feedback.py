"""Canal público de contacto y aportes de Team IGNIS.

La app no almacena aportes en Streamlit ni los publica automáticamente.
La publicación requiere que la persona confirme el Issue en GitHub.
"""
from urllib.parse import urlencode
import requests
import streamlit as st

REPO = "SaraPS1/IGNIS-UY-NASA-SPACE-APPS"
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
    """Construye URL y borrador sin enviar nada ni gestionar credenciales."""
    titulo = " ".join(str(titulo).split())[:110]
    descripcion = str(descripcion).strip()[:1500]
    referencia = str(referencia or "").strip()[:350]
    mensaje = (
        "## Contribution type\n" + categoria +
        "\n\n## Question or proposal\n" + descripcion +
        "\n\n## Source or reference (optional)\n" +
        (referencia or "Not provided") +
        "\n\n---\nPrepared in IGNIS UY."
        "Contributions remain pending review; "
        "they neither confirm wildfires nor automatically validate FIRMS data."
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
        "Share suggestions, questions, bugs, or documentary references. "
        "News reports and testimonials are contributions pending review, "
        "not automatic verification of thermal detections."
    )
    issues = estado_issues()
    if issues is False:
        st.warning(
            "GitHub Issues is disabled. To receive contributions, "
            "the team must enable it at GitHub → Settings → General "
            "→ Features → Issues. You can prepare a draft in the meantime."
        )
    elif issues is None:
        st.info(
            "Could not verify whether GitHub Issues is enabled. "
            "You can download the draft, but it has not been submitted."
        )
    else:
        st.success(
            "GitHub Issues is available: prepare your contribution "
            "and publish it from your GitHub account."
        )

    st.caption(
        "Published GitHub Issues are public. Do not include passwords, API keys, "
        "phone numbers, addresses, or third-party personal information. "
        "A GitHub account is required to publish."
    )
    with st.form("team_ignis_aporte", clear_on_submit=False):
        tipo = st.selectbox(
            "Contribution type",
            [
                "Data question",
                "Documentary source or news",
                "Report a bug",
                "Improvement suggestion",
                "Scientific or technical collaboration",
            ],
        )
        asunto = st.text_input(
            "Short title", max_chars=110,
            placeholder="Example: Wildfire report in Durazno, January 2022",
        )
        detalle = st.text_area(
            "Question or proposal", max_chars=1500, height=180,
            placeholder="Describe dates, coordinates, evidence, or the issue you found.",
        )
        referencia = st.text_input(
            "Reference link (optional)", max_chars=350,
            placeholder="https://...",
        )
        confirmado = st.checkbox(
            "I understand the Issue will be public and has not been submitted yet."
        )
        preparar = st.form_submit_button(
            "Prepare for GitHub", type="primary", use_container_width=True
        )

    if preparar:
        if len(asunto.strip()) < 8:
            st.error("Enter a title of at least 8 characters.")
        elif len(detalle.strip()) < 20:
            st.error("Describe your contribution in at least 20 characters.")
        elif referencia.strip() and not referencia.strip().startswith(("https://", "http://")):
            st.error("The reference must start with https:// or http://.")
        elif not confirmado:
            st.error("Confirm that you understand this will be public.")
        else:
            url, borrador = preparar_aporte(tipo, asunto, detalle, referencia)
            st.session_state["ignis_team_draft"] = {"url": url, "body": borrador}

    draft = st.session_state.get("ignis_team_draft")
    if draft:
        st.subheader("Draft ready")
        st.caption("Not submitted yet. Download or publish it if Issues is enabled.")
        with st.expander("View content"):
            st.code(draft["body"], language="markdown")
        st.download_button(
            "Download draft (.md)", data=draft["body"].encode("utf-8"),
            file_name="team_ignis_aporte.md", mime="text/markdown",
            use_container_width=True, key="team_draft_download",
        )
        if issues is True:
            st.link_button(
                "Continue and publish on GitHub Issues",
                draft["url"], type="primary", use_container_width=True,
            )
            st.caption(
                "GitHub requires you to sign in and confirm “Submit new issue”. "
                "IGNIS cannot verify whether you published it."
            )
        else:
            st.info(
                "The publishing link will appear when GitHub Issues "
                "is enabled and its status can be verified."
            )

    st.divider()
    st.link_button("View IGNIS UY repository", REPO_URL, use_container_width=True)
    st.caption(
        "We cannot guarantee a response or inclusion of sources without review."
    )
