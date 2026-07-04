import streamlit as st
from categories import delete_category
from persistence import save_categories


def render_sidebar():
    with st.sidebar:
        st.header("Categories")
        st.caption(
            "Categories let you group your transactions (e.g. Food, Rent, Subscriptions). "
            "Once you label a merchant, the app remembers it across all months."
        )

        st.divider()
        st.subheader("Add Category")
        new_category = st.text_input("Category name", placeholder="e.g. Groceries", key="sidebar_new_cat")
        if st.button("Add Category", type="primary", key="sidebar_add_cat") and new_category:
            if new_category not in st.session_state.categories:
                st.session_state.categories[new_category] = []
                save_categories()
                st.success(f"**{new_category}** added.")
            else:
                st.warning(f"**{new_category}** already exists.")

        st.divider()
        st.subheader("Manage Categories")
        st.caption("Click ✕ to delete a category — affected transactions revert to Uncategorized.")

        for cat in list(st.session_state.categories.keys()):
            col1, col2 = st.columns([4, 1])
            col1.write(cat)
            if cat != "Uncategorized":
                if col2.button("✕", key=f"del_cat_{cat}", help=f"Delete {cat}"):
                    delete_category(cat)
