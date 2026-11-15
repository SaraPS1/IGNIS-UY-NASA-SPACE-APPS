"""Pitch-safe view preference for IGNIS.

The page navigation, analysis filters, data, and scientific calculations are
independent of this display preference. Classic presentation is the default.
"""

MODE_KEY = "ignis_3d_explorer"


def is_explorer() -> bool:
    import streamlit as st
    return bool(st.session_state.get(MODE_KEY, False))


def set_explorer(enabled: bool = True) -> None:
    import streamlit as st
    st.session_state[MODE_KEY] = bool(enabled)


def show_explorer_entry(key: str, label: str = "Explore in 3D") -> None:
    import streamlit as st
    st.button(label, key=key, use_container_width=True,
              on_click=set_explorer, args=(True,),
              help="Show interactive 3D and printable 2D together. Original navigation and filters stay in place.")


def show_presentation_return(key: str) -> None:
    import streamlit as st
    st.button("← Back to Presentation Mode", key=key,
              on_click=set_explorer, args=(False,),
              help="Return to the original 2D-first layout without changing filters, data, or the current page.")
