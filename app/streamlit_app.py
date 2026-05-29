"""Streamlit UI for restaurant recommendations."""

import logging
import streamlit as st

from app.orchestrator import RecommendationOrchestrator
from data.models import BudgetTier, UserPreferences
from data.repository import RestaurantRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="TasteFinder - AI Restaurant Recommendations",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for design system
st.markdown("""
<style>
    /* Import DM Sans font */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    
    /* Apply design system colors */
    :root {
        --primary: #b7122a;
        --primary-container: #db313f;
        --secondary: #835500;
        --secondary-container: #feae2c;
        --surface: #f9f9f9;
        --surface-container: #eeeeee;
        --surface-container-low: #f3f3f3;
        --surface-container-lowest: #ffffff;
        --on-surface: #1a1c1c;
        --on-surface-variant: #5b403f;
        --outline: #8f6f6e;
        --error-container: #ffdad6;
    }
    
    /* Global font */
    .stApp {
        font-family: 'DM Sans', sans-serif;
        background-color: var(--surface);
        color: var(--on-surface);
    }
    
    /* Hide default sidebar */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Custom header */
    .custom-header {
        background: var(--surface);
        padding: 1rem 2rem;
        border-bottom: 1px solid var(--surface-container);
        position: sticky;
        top: 0;
        z-index: 100;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .custom-header h1 {
        color: var(--primary);
        font-size: 32px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.01em;
    }
    
    /* Main container */
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    /* Hero section */
    .hero-section {
        text-align: center;
        max-width: 800px;
        margin: 0 auto 3rem auto;
    }
    
    .hero-section h2 {
        font-size: 20px;
        font-weight: 600;
        color: var(--on-surface-variant);
        margin: 0;
    }
    
    /* Preference card */
    .preference-card {
        background: var(--surface-container-lowest);
        border-radius: 0.75rem;
        padding: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(183, 18, 42, 0.08), 0 4px 6px -2px rgba(183, 18, 42, 0.04);
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* Form labels */
    .form-label {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--on-surface-variant);
        margin-bottom: 0.5rem;
        display: block;
    }
    
    /* Custom input styling */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        background-color: var(--surface-container-low);
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 1rem;
        font-family: 'DM Sans', sans-serif;
        font-size: 16px;
        color: var(--on-surface);
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        ring: 2px solid var(--primary);
        background-color: var(--surface-container-lowest);
    }
    
    /* Budget toggle buttons */
    .budget-toggle {
        display: flex;
        background: var(--surface-container);
        padding: 0.25rem;
        border-radius: 0.5rem;
        gap: 0.25rem;
    }
    
    .budget-toggle button {
        flex: 1;
        padding: 0.5rem;
        border: none;
        background: transparent;
        border-radius: 0.375rem;
        font-family: 'DM Sans', sans-serif;
        font-size: 16px;
        font-weight: 400;
        color: var(--on-surface-variant);
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .budget-toggle button.active {
        background: var(--surface-container-lowest);
        color: var(--primary);
        font-weight: 600;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: var(--primary);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 2rem;
        font-family: 'DM Sans', sans-serif;
        font-size: 16px;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(183, 18, 42, 0.3);
        transition: all 0.2s;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: var(--primary-container);
        box-shadow: 0 6px 8px rgba(183, 18, 42, 0.4);
    }
    
    /* Recommendation cards grid */
    .recommendations-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1.5rem;
        margin-top: 2rem;
    }
    
    /* Restaurant card */
    .restaurant-card {
        background: var(--surface-container-lowest);
        border-radius: 1rem;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(183, 18, 42, 0.05);
        border: 1px solid var(--surface-container);
        transition: all 0.3s;
    }
    
    .restaurant-card:hover {
        box-shadow: 0 10px 15px rgba(183, 18, 42, 0.08);
    }
    
    /* Rank badge */
    .rank-badge {
        position: absolute;
        top: 1rem;
        left: 1rem;
        background: var(--secondary-container);
        color: #6b4500;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* AI explanation block */
    .ai-explanation {
        background: var(--error-container);
        border-left: 4px solid var(--primary);
        border-radius: 0.5rem;
        padding: 0.75rem;
        margin-top: 0.75rem;
    }
    
    .ai-explanation p {
        font-size: 14px;
        color: #93000a;
        margin: 0;
        line-height: 1.5;
    }
    
    /* Rating badge */
    .rating-badge {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        background: var(--surface-container-low);
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
        font-size: 12px;
        font-weight: 600;
    }
    
    .rating-badge .star {
        color: var(--secondary-container);
    }
    
    /* Metadata section */
    .metadata-section {
        margin-top: 2rem;
        padding-top: 1.5rem;
        border-top: 1px solid var(--surface-container);
    }
    
    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: var(--on-surface-variant);
    }
    
    /* Suggestions */
    .suggestions {
        margin-top: 1.5rem;
        text-align: left;
    }
    
    .suggestions h3 {
        font-size: 18px;
        font-weight: 600;
        color: var(--on-surface);
        margin-bottom: 1rem;
    }
    
    .suggestions ul {
        list-style: none;
        padding: 0;
    }
    
    .suggestions li {
        padding: 0.5rem 0;
        color: var(--on-surface-variant);
    }
    
    /* Mobile bottom nav */
    .bottom-nav {
        display: none;
    }
    
    @media (max-width: 768px) {
        .bottom-nav {
            display: flex;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--surface-container);
            padding: 0.75rem 1rem;
            justify-content: space-around;
            border-radius: 1rem 1rem 0 0;
            box-shadow: 0 -4px 6px rgba(0,0,0,0.1);
            z-index: 1000;
        }
        
        .bottom-nav button {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.25rem;
            background: none;
            border: none;
            color: var(--on-surface-variant);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            padding: 0.5rem;
            border-radius: 9999px;
            transition: all 0.2s;
        }
        
        .bottom-nav button.active {
            background: var(--secondary-container);
            color: #6b4500;
        }
        
        .main-container {
            padding-bottom: 5rem;
        }
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_repository():
    """Load and cache the restaurant repository."""
    return RestaurantRepository(auto_load=True)


@st.cache_resource
def get_orchestrator():
    """Load and cache the recommendation orchestrator."""
    return RecommendationOrchestrator()


def render_header():
    """Render the custom header."""
    st.markdown("""
    <div class="custom-header">
        <h1>TasteFinder</h1>
        <div style="display: flex; gap: 1rem;">
            <button style="background: none; border: none; cursor: pointer; padding: 0.5rem; border-radius: 50%;">
                <span style="font-size: 24px;">📍</span>
            </button>
            <button style="background: none; border: none; cursor: pointer; padding: 0.5rem; border-radius: 50%;">
                <span style="font-size: 24px;">�</span>
            </button>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_preferences_form():
    """Render the preference form in main content area."""
    # Get repository for dropdown values
    repository = get_repository()
    locations = repository.get_locations()
    cuisines = repository.get_cuisines()

    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Hero section
    st.markdown("""
    <div class="hero-section">
        <h2>Personalized picks from real Zomato data — filtered by you, ranked by AI</h2>
    </div>
    """, unsafe_allow_html=True)

    # Preference card
    st.markdown('<div class="preference-card">', unsafe_allow_html=True)
    
    # Two-column layout for location/budget and cuisine/rating
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<label class="form-label">Location</label>', unsafe_allow_html=True)
        location = st.selectbox(
            "location_select",
            options=locations,
            index=0 if locations else None,
            label_visibility="collapsed",
            help="Select a city or locality",
        )
        
        st.markdown('<label class="form-label">Budget</label>', unsafe_allow_html=True)
        budget = st.selectbox(
            "budget_select",
            options=[tier.value for tier in BudgetTier if tier != BudgetTier.UNKNOWN],
            index=1,  # Default to medium
            label_visibility="collapsed",
            help="Select your budget range",
        )
    
    with col2:
        st.markdown('<label class="form-label">Cuisine</label>', unsafe_allow_html=True)
        cuisine = st.multiselect(
            "cuisine_select",
            options=cuisines,
            default=[],
            label_visibility="collapsed",
            help="Select one or more cuisine types (optional)",
        )
        
        st.markdown('<label class="form-label">Minimum Rating</label>', unsafe_allow_html=True)
        min_rating = st.slider(
            "rating_slider",
            min_value=0.0,
            max_value=5.0,
            value=3.5,
            step=0.1,
            label_visibility="collapsed",
            help="Minimum restaurant rating (0.0 to 5.0)",
        )
    
    # Full width section for extras and top_n
    st.markdown('<div style="border-top: 1px solid var(--surface-container); margin-top: 1.5rem; padding-top: 1.5rem;">', unsafe_allow_html=True)
    
    st.markdown('<label class="form-label">Additional Preferences</label>', unsafe_allow_html=True)
    extras = st.text_input(
        "extras_input",
        placeholder="e.g., family-friendly, outdoor, rooftop",
        label_visibility="collapsed",
        help="Additional keywords to search for (comma-separated, optional)",
    )
    
    # Results count and submit button
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<label class="form-label">Results</label>', unsafe_allow_html=True)
        top_n = st.slider(
            "top_n_slider",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
            label_visibility="collapsed",
            help="How many recommendations to show",
        )
    
    with col2:
        st.markdown('<br>', unsafe_allow_html=True)
        submitted = st.button("Get recommendations →", type="primary", use_container_width=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    return {
        "location": location,
        "budget": budget,
        "cuisine": cuisine,
        "min_rating": min_rating,
        "extras": extras,
        "top_n": top_n,
        "submitted": submitted,
    }


def render_recommendation_card(rec, index):
    """Render a single recommendation card with design system styling."""
    r = rec.restaurant

    # Card container with custom styling
    st.markdown(f"""
    <div class="restaurant-card" style="position: relative;">
        <div class="rank-badge">Rank #{rec.rank}</div>
        <div style="padding: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
                <div>
                    <h3 style="font-size: 20px; font-weight: 600; margin: 0; color: var(--on-surface);">{r.name}</h3>
                    <p style="font-size: 14px; color: var(--on-surface-variant); margin: 0.25rem 0 0 0;">
                        {', '.join(r.cuisines[:3])}{' • ' if r.cost_for_two else ''}{'₹' + str(r.cost_for_two) + ' for two' if r.cost_for_two else ''}
                    </p>
                </div>
                <div class="rating-badge">
                    <span class="star">★</span>
                    <span>{r.rating}</span>
                </div>
            </div>
            <div class="ai-explanation">
                <p>{rec.explanation}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_empty_state(filter_stats):
    """Render empty state with design system styling."""
    st.markdown("""
    <div class="empty-state">
        <div style="font-size: 48px; margin-bottom: 1rem;">🔍</div>
        <h3 style="font-size: 20px; font-weight: 600; margin-bottom: 0.5rem;">No restaurants match your criteria</h3>
    </div>
    """, unsafe_allow_html=True)

    if filter_stats and filter_stats.suggestions:
        st.markdown('<div class="suggestions">', unsafe_allow_html=True)
        st.markdown("<h3>💡 Suggestions to find more results</h3>")
        for suggestion in filter_stats.suggestions:
            st.markdown(f"<li>{suggestion}</li>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="suggestions">', unsafe_allow_html=True)
        st.markdown("<h3>💡 Tips</h3>")
        st.markdown("<li>Try a different location</li>", unsafe_allow_html=True)
        st.markdown("<li>Try a different cuisine</li>", unsafe_allow_html=True)
        st.markdown("<li>Lower your minimum rating</li>", unsafe_allow_html=True)
        st.markdown("<li>Try a different budget tier</li>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_metadata(response):
    """Render metadata and filter stats with design system styling."""
    st.markdown('<div class="metadata-section">', unsafe_allow_html=True)
    
    with st.expander("📊 Search details & metrics"):
        st.markdown(f"""
        <div style="font-size: 14px; color: var(--on-surface-variant); line-height: 1.5;">
            <p style="margin: 0.5rem 0;">Candidates considered: {response.metadata.total_candidates}</p>
            <p style="margin: 0.5rem 0;">AI explanations available: {'Yes' if response.metadata.ai_explanations_available else 'No'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if response.filter_stats:
            filters_text = ", ".join([f"{k}: {v}" for k, v in response.filter_stats.filters_applied.items()])
            st.markdown(f"""
            <div style="font-size: 14px; color: var(--on-surface-variant); line-height: 1.5;">
                <p style="margin: 0.5rem 0;">Filters applied: {filters_text}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main Streamlit app."""
    # Render custom header
    render_header()
    
    # Render preferences form
    prefs = render_preferences_form()
    
    # Check if form was submitted
    if not prefs["submitted"]:
        st.markdown("""
        <div class="empty-state">
            <div style="font-size: 48px; margin-bottom: 1rem;">🍽️</div>
            <p style="font-size: 16px; color: var(--on-surface-variant);">Set your preferences and we'll find the best spots for you.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Add bottom navigation for mobile
        render_bottom_nav()
        return

    # Parse extras
    extras_list = [e.strip() for e in prefs["extras"].split(",") if e.strip()] if prefs["extras"] else []

    # Create UserPreferences
    try:
        preferences = UserPreferences(
            location=prefs["location"],
            budget=BudgetTier(prefs["budget"]),
            cuisine=prefs["cuisine"],
            min_rating=prefs["min_rating"],
            extras=extras_list,
            top_n=prefs["top_n"],
        )
    except Exception as e:
        st.error(f"❌ Invalid preferences: {e}")
        return

    # Show loading spinner
    with st.spinner("🤖 AI is analyzing restaurants and generating personalized recommendations..."):
        try:
            orchestrator = get_orchestrator()
            response = orchestrator.recommend(preferences)
        except Exception as e:
            st.error(f"❌ Error generating recommendations: {e}")
            logger.error("Error generating recommendations", exc_info=True)
            return

    # Display message if present
    if response.message:
        if response.metadata.ai_explanations_available:
            st.markdown(f"""
            <div style="background: #dcfce7; color: #166534; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;">
                {response.message}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: #fef9c3; color: #854d0e; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;">
                {response.message}
            </div>
            """, unsafe_allow_html=True)

    # Display recommendations or empty state
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    if response.recommendations:
        st.markdown(f"<h2 style='font-size: 24px; font-weight: 700; margin: 2rem 0 1rem 0;'>Top {len(response.recommendations)} Recommendations</h2>", unsafe_allow_html=True)

        # Display summary if available
        if response.summary:
            st.markdown(f"""
            <div style="background: var(--primary-fixed); border-radius: 0.75rem; padding: 1rem 1.5rem; margin-bottom: 1.5rem; display: flex; align-items: flex-start; gap: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="background: var(--surface-container-lowest); padding: 0.5rem; border-radius: 50%; color: var(--primary);">
                    <span style="font-size: 20px;">✨</span>
                </div>
                <div>
                    <h3 style="font-size: 18px; font-weight: 600; margin: 0 0 0.25rem 0; color: var(--on-primary-fixed);">AI Recommendation</h3>
                    <p style="font-size: 16px; margin: 0; color: var(--on-primary-fixed-variant); opacity: 0.9;">{response.summary}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Render recommendation cards in grid
        st.markdown('<div class="recommendations-grid">', unsafe_allow_html=True)
        for i, rec in enumerate(response.recommendations):
            render_recommendation_card(rec, i)
        st.markdown('</div>', unsafe_allow_html=True)

        # Render metadata
        render_metadata(response)
    else:
        render_empty_state(response.filter_stats)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Add bottom navigation for mobile
    render_bottom_nav()


def render_bottom_nav():
    """Render bottom navigation bar for mobile."""
    st.markdown("""
    <div class="bottom-nav">
        <button class="active">
            <span>🧭</span>
            <span>Explore</span>
        </button>
        <button>
            <span>🔖</span>
            <span>Saved</span>
        </button>
        <button>
            <span>📜</span>
            <span>History</span>
        </button>
        <button>
            <span>👤</span>
            <span>Profile</span>
        </button>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
