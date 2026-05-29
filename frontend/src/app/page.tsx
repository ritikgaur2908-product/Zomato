"use client";

import React, { useState, useEffect, useRef } from "react";
import metadata from "./metadata.json";
import Logo from "./components/Logo";

type UIState = "home" | "loading" | "results" | "empty" | "error";

interface Restaurant {
  id: string;
  name: string;
  location: string;
  city: string;
  cuisines: string[];
  rating: number;
  cost_for_two: number | null;
  budget_tier: string;
  raw: any;
}

interface RankedRecommendation {
  restaurant: Restaurant;
  rank: number;
  explanation: string;
  match_highlights: string[];
}

interface RecommendationResponse {
  recommendations: RankedRecommendation[];
  summary: string | null;
  message: string | null;
  metadata: {
    total_candidates: number;
    filters_applied: Record<string, any>;
    ai_explanations_available: boolean;
    parse_used_fallback: boolean;
    llm_attempts: number;
    stripped_invalid_ids: number;
  };
  filter_stats?: {
    input_count: number;
    output_count: number;
    capped_to: number | null;
    filters_applied: Record<string, any>;
    relaxed_filters: string[];
    suggestions: string[];
  };
}

const getRestaurantImage = (name: string, cuisines: string[] = []): string => {
  const lowerName = name.toLowerCase();
  
  if (lowerName.includes("truffles")) {
    return "https://images.unsplash.com/photo-1546549032-9571cd6b27df?w=600&auto=format&fit=crop&q=80";
  }
  if (lowerName.includes("toit")) {
    return "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&auto=format&fit=crop&q=80";
  }

  const cuisinesStr = cuisines.map(c => c.toLowerCase()).join(" ");
  if (cuisinesStr.includes("pizza")) {
    return "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&auto=format&fit=crop&q=80";
  }
  if (cuisinesStr.includes("pasta") || cuisinesStr.includes("italian")) {
    return "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&auto=format&fit=crop&q=80";
  }
  if (cuisinesStr.includes("cafe") || cuisinesStr.includes("coffee") || cuisinesStr.includes("beverages")) {
    return "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=600&auto=format&fit=crop&q=80";
  }
  if (cuisinesStr.includes("chinese") || cuisinesStr.includes("asian") || cuisinesStr.includes("momos")) {
    return "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=600&auto=format&fit=crop&q=80";
  }
  if (cuisinesStr.includes("biryani") || cuisinesStr.includes("kebab") || cuisinesStr.includes("mughlai")) {
    return "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&auto=format&fit=crop&q=80";
  }
  if (cuisinesStr.includes("south indian") || cuisinesStr.includes("andhra") || cuisinesStr.includes("kerala")) {
    return "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=600&auto=format&fit=crop&q=80";
  }
  if (cuisinesStr.includes("desserts") || cuisinesStr.includes("ice cream") || cuisinesStr.includes("mithai") || cuisinesStr.includes("bakery")) {
    return "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=600&auto=format&fit=crop&q=80";
  }
  if (cuisinesStr.includes("burger") || cuisinesStr.includes("sandwich") || cuisinesStr.includes("fast food")) {
    return "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&auto=format&fit=crop&q=80";
  }
  
  return "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&auto=format&fit=crop&q=80";
};

const getExplanationIcon = (explanation: string): string => {
  const exp = explanation.toLowerCase();
  if (exp.includes("group") || exp.includes("crowd") || exp.includes("friends")) {
    return "group";
  }
  if (exp.includes("romantic") || exp.includes("date") || exp.includes("ambience") || exp.includes("wine")) {
    return "wine_bar";
  }
  if (exp.includes("quick") || exp.includes("fast") || exp.includes("speed")) {
    return "speed";
  }
  if (exp.includes("budget") || exp.includes("price") || exp.includes("value")) {
    return "payments";
  }
  if (exp.includes("family") || exp.includes("kids") || exp.includes("friendly")) {
    return "family_restroom";
  }
  if (exp.includes("pizza") || exp.includes("pasta") || exp.includes("italian") || exp.includes("authentic")) {
    return "restaurant";
  }
  return "tips_and_updates";
};

export default function TasteFinderApp() {
  const [state, setState] = useState<UIState>("home");
  const [errorDetails, setErrorDetails] = useState<string>("Could not fetch recommendations.");
  const [response, setResponse] = useState<RecommendationResponse | null>(null);

  const [selectedLocation, setSelectedLocation] = useState<string>("");
  const [selectedBudget, setSelectedBudget] = useState<"low" | "medium" | "high">("medium");
  const [cuisineInput, setCuisineInput] = useState<string>("");
  const [selectedCuisines, setSelectedCuisines] = useState<string[]>([]);
  const [minRating, setMinRating] = useState<number>(4.0);
  const [extras, setExtras] = useState<string>("");
  const [topN, setTopN] = useState<number>(5);

  const [locationSearch, setLocationSearch] = useState<string>("");
  const [showLocationDropdown, setShowLocationDropdown] = useState<boolean>(false);
  const [showCuisineDropdown, setShowCuisineDropdown] = useState<boolean>(false);
  const [bookmarkedIds, setBookmarkedIds] = useState<string[]>([]);
  const [loadingStep, setLoadingStep] = useState<number>(0);

  const locationRef = useRef<HTMLDivElement>(null);
  const cuisineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("tastefinder_bookmarks");
      if (saved) {
        setBookmarkedIds(JSON.parse(saved));
      }
    } catch (e) {
      console.error("Failed to load bookmarks", e);
    }
  }, []);

  const toggleBookmark = (id: string) => {
    let updated;
    if (bookmarkedIds.includes(id)) {
      updated = bookmarkedIds.filter((b) => b !== id);
    } else {
      updated = [...bookmarkedIds, id];
    }
    setBookmarkedIds(updated);
    localStorage.setItem("tastefinder_bookmarks", JSON.stringify(updated));
  };

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (locationRef.current && !locationRef.current.contains(event.target as Node)) {
        setShowLocationDropdown(false);
      }
      if (cuisineRef.current && !cuisineRef.current.contains(event.target as Node)) {
        setShowCuisineDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (state === "loading") {
      setLoadingStep(0);
      interval = setInterval(() => {
        setLoadingStep((prev) => (prev + 1) % 3);
      }, 1500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [state]);

  // Show icons once Material Symbols font has loaded
  useEffect(() => {
    document.fonts.ready.then(() => {
      document.body.classList.add("icons-loaded");
    });
  }, []);

  const filteredLocations = locationSearch.trim() === ""
    ? metadata.locations
    : metadata.locations.filter((loc) =>
        loc.toLowerCase().includes(locationSearch.toLowerCase())
      );

  const filteredCuisines = metadata.cuisines.filter(
    (c) =>
      c.toLowerCase().includes(cuisineInput.toLowerCase()) &&
      !selectedCuisines.includes(c)
  );

  const handleSubmit = async () => {
    if (!selectedLocation && !locationSearch.trim()) {
      setErrorDetails("Please select or type a location to get recommendations.");
      setState("error");
      return;
    }
    setState("loading");
    try {
      const payload = {
        location: selectedLocation || locationSearch,
        budget: selectedBudget,
        cuisine: selectedCuisines,
        min_rating: minRating,
        top_n: topN,
        extras: extras,
      };

      const res = await fetch("/api/recommendations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.details ? `${data.error}: ${data.details}` : (data.error || "Failed to fetch recommendations"));
      }

      const data: RecommendationResponse = await res.json();
      setResponse(data);

      if (!data.recommendations || data.recommendations.length === 0) {
        setState("empty");
      } else {
        setState("results");
      }
    } catch (err: any) {
      console.error(err);
      setErrorDetails(err.message || "Something went wrong.");
      setState("error");
    }
  };

  return (
    <div className="bg-background text-onBackground min-h-screen flex flex-col antialiased">
      {/* TopAppBar */}
      <header className="bg-surface dark:bg-surface border-b border-surfaceContainer flex justify-between items-center w-full px-md h-16 max-w-containerMax mx-auto top-0 sticky z-40">
        <div className="flex items-center gap-2 cursor-pointer animate-fade-in" onClick={() => setState("home")}>
          <Logo className="w-8 h-8 object-contain" />
          <h1 className="font-displayLg text-headlineLgMobile md:text-headlineLg text-primary tracking-tight">
            TasteFinder
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button className="hover:bg-surfaceContainerLow transition-colors p-2 rounded-full flex items-center justify-center active:scale-95 duration-150 text-onSurfaceVariant" aria-label="Location">
            <span className="material-symbols-outlined text-[22px]">location_on</span>
          </button>
          <button className="hover:bg-surfaceContainerLow transition-colors p-2 rounded-full flex items-center justify-center active:scale-95 duration-150 text-onSurfaceVariant" aria-label="Notifications">
            <span className="material-symbols-outlined text-[22px]">notifications</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-grow w-full max-w-containerMax mx-auto px-md md:px-lg py-lg md:py-xl flex flex-col gap-lg pb-24 md:pb-12">
        
        {/* HOME STATE */}
        {state === "home" && (
          <div className="w-full flex flex-col gap-lg animate-fade-in">
            {/* Hero Section */}
            <section className="text-center max-w-2xl mx-auto mb-2">
              <h2 className="font-titleMd text-titleMd text-onSurfaceVariant mb-2">
                Personalized picks from real Zomato data — filtered by you, ranked by AI
              </h2>
            </section>

            {/* Main Preference Card (Bento Layout) */}
            <div className="elevation-2 rounded-xl p-md md:p-lg max-w-4xl w-full mx-auto grid grid-cols-1 md:grid-cols-2 gap-lg relative bg-surfaceContainerLowest">
              
              {/* Left Column: Location & Budget */}
              <div className="space-y-6">
                
                {/* Location Input with Dropdown */}
                <div ref={locationRef} className="relative">
                  <label className="font-labelMd text-labelMd text-onSurfaceVariant block mb-2 uppercase tracking-wider">
                    Location
                  </label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-primary text-[20px] pointer-events-none">
                      location_on
                    </span>
                    <input
                      className="w-full h-12 pl-10 pr-4 bg-surfaceContainerLow border-2 border-transparent rounded-lg focus:border-primary focus:bg-surfaceContainerLowest transition-colors font-bodyLg text-bodyLg text-onSurface placeholder:text-onSurfaceVariant/50"
                      placeholder="Search a location..."
                      type="text"
                      value={locationSearch}
                      onChange={(e) => {
                        setLocationSearch(e.target.value);
                        setSelectedLocation("");
                        setShowLocationDropdown(true);
                      }}
                      onFocus={() => setShowLocationDropdown(true)}
                    />
                  </div>

                  {showLocationDropdown && filteredLocations.length > 0 && (
                    <ul className="absolute left-0 right-0 mt-1 max-h-60 overflow-y-auto custom-scrollbar bg-surfaceContainerLowest border border-surfaceContainer rounded-lg shadow-lg z-[100] py-1">
                      {filteredLocations.slice(0, 30).map((loc) => (
                        <li
                          key={loc}
                          className={`px-4 py-2.5 hover:bg-surfaceContainerLow cursor-pointer text-sm text-onSurface transition-colors ${
                            loc === selectedLocation ? "bg-surfaceContainerLow font-semibold text-primary" : ""
                          }`}
                          onClick={() => {
                            setSelectedLocation(loc);
                            setLocationSearch(loc);
                            setShowLocationDropdown(false);
                          }}
                        >
                          {loc}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Budget Tabs */}
                <div>
                  <label className="font-labelMd text-labelMd text-onSurfaceVariant block mb-2 uppercase tracking-wider">
                    Budget
                  </label>
                  <div className="flex bg-surfaceContainerHigh p-1 rounded-lg">
                    {(["low", "medium", "high"] as const).map((tier) => (
                      <button
                        key={tier}
                        className={`flex-1 py-2 text-center rounded-md transition-all font-titleMd text-titleMd ${
                          selectedBudget === tier
                            ? "bg-surfaceContainerLowest shadow-sm text-primary font-bold"
                            : "text-onSurfaceVariant hover:text-onSurface"
                        }`}
                        onClick={() => setSelectedBudget(tier)}
                      >
                        {tier.charAt(0).toUpperCase() + tier.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Column: Cuisine & Rating */}
              <div className="space-y-6">
                
                {/* Cuisine Multi-select and Search */}
                <div ref={cuisineRef} className="relative">
                  <label className="font-labelMd text-labelMd text-onSurfaceVariant block mb-2 uppercase tracking-wider">
                    Cuisine
                  </label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-onSurfaceVariant text-[20px] pointer-events-none">
                      restaurant
                    </span>
                    <input
                      className="w-full h-12 pl-10 pr-4 bg-surfaceContainerLow border-2 border-transparent rounded-lg focus:border-primary focus:bg-surfaceContainerLowest transition-colors font-bodyLg text-bodyLg text-onSurface placeholder:text-onSurfaceVariant/50"
                      placeholder="Search cuisines..."
                      type="text"
                      value={cuisineInput}
                      onChange={(e) => {
                        setCuisineInput(e.target.value);
                        setShowCuisineDropdown(true);
                      }}
                      onFocus={() => setShowCuisineDropdown(true)}
                    />
                  </div>
                
                  {showCuisineDropdown && filteredCuisines.length > 0 && (
                    <ul className="absolute left-0 right-0 mt-1 max-h-60 overflow-y-auto custom-scrollbar bg-surfaceContainerLowest border border-surfaceContainer rounded-lg shadow-lg z-[100] py-1">
                      {filteredCuisines.slice(0, 30).map((c) => (
                        <li
                          key={c}
                          className="px-4 py-2.5 hover:bg-surfaceContainerLow cursor-pointer text-sm text-onSurface transition-colors"
                          onClick={() => {
                            setSelectedCuisines([...selectedCuisines, c]);
                            setCuisineInput("");
                            setShowCuisineDropdown(false);
                          }}
                        >
                          {c}
                        </li>
                      ))}
                    </ul>
                  )}
                
                  {/* Selected Cuisine Pills */}
                  {selectedCuisines.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {selectedCuisines.map((c) => (
                        <span
                          key={c}
                          className="inline-flex items-center gap-1 bg-primary/10 border border-primary/20 text-primary text-sm px-3 py-1 rounded-full animate-fade-in"
                        >
                          {c}
                          <button
                            type="button"
                            onClick={() => setSelectedCuisines(selectedCuisines.filter((item) => item !== c))}
                            className="font-bold hover:text-primaryContainer ml-0.5 focus:outline-none text-primary"
                          >
                            \u00d7
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Rating Slider */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="font-labelMd text-labelMd text-onSurfaceVariant uppercase tracking-wider">
                      Minimum Rating
                    </label>
                    <span className="text-sm font-semibold text-primary flex items-center gap-1">
                      <span>{minRating.toFixed(1)}</span>
                      <span className="material-symbols-outlined filled text-secondaryContainer text-[16px]">star</span>
                    </span>
                  </div>
                  <div className="pt-2">
                    <input
                      className="w-full cursor-pointer"
                      id="rating-slider"
                      max="5"
                      min="0"
                      step="0.1"
                      type="range"
                      value={minRating}
                      onChange={(e) => setMinRating(parseFloat(e.target.value))}
                    />
                    <div className="flex justify-between text-xs text-onSurfaceVariant mt-1">
                      <span>0.0</span>
                      <span>5.0</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bento Full-Width Row: Extras, Stepper, Submit */}
              <div className="md:col-span-2 space-y-6 border-t border-surfaceVariant pt-6 mt-2">
                
                {/* Additional Preferences */}
                <div>
                  <label className="font-labelMd text-labelMd text-onSurfaceVariant block mb-2 uppercase tracking-wider">
                    Additional Preferences
                  </label>
                  <textarea
                    className="w-full p-4 bg-surfaceContainerLow border-2 border-transparent rounded-lg focus:border-primary focus:bg-surfaceContainerLowest transition-colors text-base text-onSurface placeholder:text-onSurfaceVariant/50 resize-none"
                    placeholder="e.g. family-friendly, quick service, outdoor seating, rooftop..."
                    rows={2}
                    value={extras}
                    onChange={(e) => setExtras(e.target.value)}
                  />
                </div>

                {/* Stepper + CTA button */}
                <div className="flex flex-col sm:flex-row items-center gap-4 justify-between">
                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    <label className="font-labelMd text-labelMd text-onSurfaceVariant uppercase tracking-wider whitespace-nowrap">
                      Results:
                    </label>
                    <div className="flex items-center bg-surfaceContainerHigh rounded-lg p-1">
                      <button
                        className="w-9 h-9 flex items-center justify-center rounded-md bg-surfaceContainerLowest text-onSurface hover:bg-surfaceVariant transition-colors disabled:opacity-40"
                        onClick={() => setTopN(Math.max(1, topN - 1))}
                        disabled={topN <= 1}
                        aria-label="Decrease"
                      >
                        <span className="material-symbols-outlined text-[20px]">remove</span>
                      </button>
                      <span className="w-10 text-center text-base font-semibold text-onSurface">
                        {topN}
                      </span>
                      <button
                        className="w-9 h-9 flex items-center justify-center rounded-md bg-surfaceContainerLowest text-onSurface hover:bg-surfaceVariant transition-colors disabled:opacity-40"
                        onClick={() => setTopN(Math.min(20, topN + 1))}
                        disabled={topN >= 20}
                        aria-label="Increase"
                      >
                        <span className="material-symbols-outlined text-[20px]">add</span>
                      </button>
                    </div>
                  </div>

                  <button
                    onClick={handleSubmit}
                    className="w-full sm:w-auto bg-primary hover:bg-primaryContainer text-onPrimary text-base font-semibold py-3 px-8 rounded-lg shadow-md hover:shadow-lg transition-all active:scale-95 inline-flex items-center justify-center gap-2 min-h-[48px]"
                  >
                    <span>Get recommendations</span>
                    <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Empty State Banner when idle */}
            <div className="mt-6 text-center flex flex-col items-center justify-center opacity-70">
              <div className="w-24 h-24 bg-surfaceContainerLow rounded-full flex items-center justify-center mb-4 border border-surfaceContainer">
                <span className="material-symbols-outlined text-4xl text-primary">
                  restaurant_menu
                </span>
              </div>
              <p className="font-bodyLg text-bodyLg text-onSurfaceVariant max-w-sm">
                Set your preferences and we'll find the best spots for you.
              </p>
            </div>
          </div>
        )}

        {/* LOADING STATE */}
        {state === "loading" && (
          <div className="relative flex-grow w-full overflow-hidden min-h-[400px] flex items-center justify-center animate-fade-in">
            {/* Faded background skeleton loaders */}
            <div aria-hidden="true" className="w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-lg opacity-25 select-none pointer-events-none">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-surfaceContainerLowest rounded-xl border border-surfaceContainer overflow-hidden flex flex-col h-[380px]">
                  <div className="h-48 bg-surfaceVariant animate-pulse w-full"></div>
                  <div className="p-md flex flex-col gap-sm flex-grow">
                    <div className="h-6 bg-surfaceVariant rounded w-3/4 animate-pulse"></div>
                    <div className="h-4 bg-surfaceVariant rounded w-1/2 animate-pulse mb-4"></div>
                    <div className="flex gap-2 mb-auto">
                      <div className="h-6 w-16 bg-surfaceVariant rounded-full animate-pulse"></div>
                      <div className="h-6 w-20 bg-surfaceVariant rounded-full animate-pulse"></div>
                    </div>
                  </div>
                  <div className="bg-errorContainer/20 p-sm border-l-4 border-primaryFixedDim h-20 flex flex-col justify-center px-md gap-2">
                    <div className="h-3 bg-surfaceVariant rounded w-5/6 animate-pulse"></div>
                  </div>
                </div>
              ))}
            </div>

            {/* Loading Overlay Dialog */}
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
              <div className="bg-surfaceContainerLowest p-xl rounded-2xl shadow-lg border border-surfaceContainer flex flex-col items-center max-w-lg w-[calc(100%-32px)] text-center">
                <div className="w-16 h-16 border-4 border-surfaceContainer border-t-primary rounded-full animate-spin mb-lg"></div>
                <h2 className="font-headlineLgMobile md:text-headlineLg text-onSurface mb-md">
                  Finding and ranking restaurants…
                </h2>
                
                {/* Step indicator animations */}
                <div className="flex flex-col md:flex-row items-center justify-center gap-sm md:gap-md mt-sm w-full font-bodySm text-bodySm text-onSurfaceVariant">
                  <div className={`flex items-center gap-2 transition-all duration-300 ${loadingStep === 0 ? "text-primary font-bold opacity-100 scale-105" : loadingStep > 0 ? "opacity-75 text-onSurface" : "opacity-40"}`}>
                    <span className="material-symbols-outlined text-[18px]">tune</span>
                    <span>Filtering matches</span>
                  </div>
                  <span className="material-symbols-outlined text-[16px] text-surfaceVariant hidden md:block">arrow_forward</span>
                  <span className="material-symbols-outlined text-[16px] text-surfaceVariant block md:hidden rotate-90">arrow_forward</span>
                  
                  <div className={`flex items-center gap-2 transition-all duration-300 ${loadingStep === 1 ? "text-primary font-bold opacity-100 scale-105" : loadingStep > 1 ? "opacity-75 text-onSurface" : "opacity-40"}`}>
                    <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                    <span>Asking AI</span>
                  </div>
                  <span className="material-symbols-outlined text-[16px] text-surfaceVariant hidden md:block">arrow_forward</span>
                  <span className="material-symbols-outlined text-[16px] text-surfaceVariant block md:hidden rotate-90">arrow_forward</span>
                  
                  <div className={`flex items-center gap-2 transition-all duration-300 ${loadingStep === 2 ? "text-primary font-bold opacity-100 scale-105" : "opacity-40"}`}>
                    <span className="material-symbols-outlined text-[18px]">list_alt</span>
                    <span>Preparing list</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* RESULTS STATE */}
        {state === "results" && response && (
          <div className="w-full flex flex-col gap-lg animate-fade-in">
            
            {/* Warning alerts: Degraded AI State warning */}
            {!response.metadata.ai_explanations_available && (
              <div className="bg-[#FFF8E1] border-l-4 border-secondaryContainer p-md rounded-r-lg flex items-start gap-md shadow-sm">
                <span className="material-symbols-outlined text-secondaryContainer mt-1">warning</span>
                <div>
                  <h3 className="font-titleMd text-titleMd text-onSecondaryFixed text-sm md:text-base mb-xs">
                    AI ranking unavailable
                  </h3>
                  <p className="font-bodySm text-bodySm text-onSecondaryFixedVariant">
                    {response.message || "Showing top-rated matches from your filters instead of AI-personalized recommendations right now."}
                  </p>
                </div>
              </div>
            )}

            {/* Section A: AI Summary Banner (Only if available) */}
            {response.summary && (
              <section className="bg-primaryFixed rounded-xl p-md md:p-lg flex items-start gap-md shadow-sm border border-primaryFixedDim">
                <div className="mt-1 bg-surfaceContainerLowest p-2 rounded-full shadow-sm text-primary">
                  <span className="material-symbols-outlined filled">auto_awesome</span>
                </div>
                <div>
                  <h2 className="font-titleMd text-titleMd text-onPrimaryFixed mb-xs">
                    AI Recommendation
                  </h2>
                  <p className="font-bodyLg text-bodyLg text-onPrimaryFixedVariant opacity-90">
                    {response.summary}
                  </p>
                </div>
              </section>
            )}

            {/* Section B: Recommendation Bento Grid */}
            <section className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-md lg:gap-lg ${
              !response.metadata.ai_explanations_available ? "opacity-85" : ""
            }`}>
              {response.recommendations.map((rec, index) => {
                const r = rec.restaurant;
                const isLargeCard = index === 0;
                return (
                  <article
                    key={r.id}
                    className={`bg-surfaceContainerLowest rounded-xl overflow-hidden shadow-md border border-surfaceContainer hover:shadow-lg transition-all duration-300 flex flex-col ${
                      isLargeCard ? "md:col-span-2 lg:col-span-2" : ""
                    }`}
                  >
                    {/* Header Image */}
                    <div className={`relative w-full ${isLargeCard ? "h-48 md:h-64" : "h-48"}`}>
                      <img
                        alt={r.name}
                        className="w-full h-full object-cover"
                        src={getRestaurantImage(r.name, r.cuisines)}
                      />
                      
                      {/* Rank badge */}
                      <div className="absolute top-md left-md bg-secondaryContainer text-onSecondaryContainer px-sm py-xs rounded-full inline-flex items-center gap-1 text-xs font-semibold shadow-sm border border-secondaryContainer/20">
                        <span className="material-symbols-outlined text-[14px] filled">workspace_premium</span>
                        <span>Rank #{rec.rank}</span>
                      </div>

                      {/* Bookmark button */}
                      <button
                        onClick={() => toggleBookmark(r.id)}
                        className={`absolute top-md right-md p-2 bg-surfaceContainerLowest/80 backdrop-blur-sm rounded-full transition-colors active:scale-95 duration-100 ${
                          bookmarkedIds.includes(r.id) ? "text-primary" : "text-onSurface hover:text-primary"
                        }`}
                      >
                        <span className={`material-symbols-outlined ${bookmarkedIds.includes(r.id) ? "filled" : ""}`}>
                          bookmark
                        </span>
                      </button>
                    </div>

                    {/* Details content */}
                    <div className="p-md flex-grow flex flex-col">
                      <div className="flex justify-between items-start mb-sm">
                        <div>
                          <h3 className="font-titleMd text-titleMd text-onSurface">
                            {r.name}
                          </h3>
                          <p className="font-bodySm text-bodySm text-onSurfaceVariant flex items-center gap-xs mt-1">
                            {r.cuisines.slice(0, 3).join(" • ")}
                            {r.cost_for_two ? (
                              <>
                                <span className="text-tertiaryFixedDim text-xs">•</span>
                                <span>₹{r.cost_for_two} for two</span>
                              </>
                            ) : null}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 bg-surfaceContainerLow px-2 py-1 rounded-md shrink-0">
                          <span className="material-symbols-outlined text-secondaryContainer text-[16px] filled">star</span>
                          <span className="text-xs font-semibold text-onSurface">{r.rating.toFixed(1)}</span>
                        </div>
                      </div>

                      {/* AI Explanation Block */}
                      <div className="mt-auto pt-sm">
                        <div className="bg-errorContainer/40 rounded-lg p-sm border-l-4 border-primary flex gap-sm items-start">
                          <span className="material-symbols-outlined text-primary text-[20px] mt-0.5">
                            {getExplanationIcon(rec.explanation)}
                          </span>
                          <p className="font-bodySm text-bodySm text-onErrorContainer">
                            {rec.explanation}
                          </p>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </section>

            {/* Footer search details */}
            <div className="mt-lg border-t border-surfaceContainer pt-md">
              <details className="group cursor-pointer">
                <summary className="flex items-center gap-2 text-xs font-semibold text-onSurfaceVariant select-none opacity-80 hover:opacity-100 transition-opacity">
                  <span className="material-symbols-outlined text-[18px] transition-transform duration-200 group-open:rotate-180">expand_more</span>
                  Search details &amp; metrics
                </summary>
                <div className="mt-sm pl-8 font-bodySm text-bodySm text-onSurfaceVariant flex flex-col gap-1 opacity-75">
                  <p>Candidates considered: {response.metadata.total_candidates}</p>
                  <p>
                    Filters applied: {selectedLocation}
                    {selectedCuisines.length > 0 ? `, Cuisines: [${selectedCuisines.join(", ")}]` : ""}
                    , Budget: {selectedBudget}
                    , Min Rating: {minRating.toFixed(1)}+
                    {extras ? `, Keywords: "${extras}"` : ""}
                  </p>
                  <p>AI explanations available: {response.metadata.ai_explanations_available ? "Yes" : "No"}</p>
                  {response.metadata.llm_attempts > 1 && (
                    <p>LLM attempts: {response.metadata.llm_attempts}</p>
                  )}
                  {response.metadata.parse_used_fallback && (
                    <p>Parse fallback used: Yes</p>
                  )}
                </div>
              </details>
            </div>

            {/* Back to preference form */}
            <div className="flex justify-center mt-6">
              <button
                onClick={() => setState("home")}
                className="bg-surface border-2 border-primary text-primary hover:bg-surfaceContainerLow text-sm font-semibold py-2.5 px-6 rounded-lg transition-colors inline-flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-[20px]">arrow_back</span>
                <span>Adjust preferences</span>
              </button>
            </div>
          </div>
        )}

        {/* EMPTY STATE */}
        {state === "empty" && (
          <section className="bg-surfaceContainerLowest border border-surfaceContainer rounded-xl p-lg md:p-xl flex flex-col items-center justify-center text-center min-h-[400px] shadow-sm relative overflow-hidden animate-fade-in">
            {/* Decorative backgrounds */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-surfaceContainerLow rounded-full mix-blend-multiply filter blur-3xl opacity-50 transform translate-x-1/2 -translate-y-1/2"></div>
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-errorContainer rounded-full mix-blend-multiply filter blur-3xl opacity-30 transform -translate-x-1/2 translate-y-1/2"></div>
            
            <div className="relative z-10 flex flex-col items-center max-w-md mx-auto">
              <div className="w-24 h-24 bg-surfaceContainer rounded-full flex items-center justify-center mb-md shadow-sm border border-surfaceContainer">
                <span className="material-symbols-outlined text-4xl text-onSurfaceVariant" style={{ fontSize: "48px" }}>
                  restaurant_menu
                </span>
              </div>
              <h2 className="font-titleMd text-titleMd text-onBackground mb-sm">
                No restaurants match
              </h2>
              <p className="font-bodyLg text-bodyLg text-onSurfaceVariant mb-lg">
                {response?.message || "We couldn't find any spots matching all your current filters. Try broadening your search to discover more options."}
              </p>
              
              {/* suggestions lists if present */}
              {response?.filter_stats?.suggestions && response.filter_stats.suggestions.length > 0 && (
                <div className="text-left w-full bg-surfaceContainerLow rounded-lg p-4 mb-6 border border-surfaceContainer">
                  <h4 className="font-labelMd text-labelMd text-primary mb-2 uppercase tracking-wide">Suggestions:</h4>
                  <ul className="list-disc list-inside space-y-1 font-bodySm text-bodySm text-onSurfaceVariant">
                    {response.filter_stats.suggestions.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              <button
                onClick={() => setState("home")}
                className="bg-primary text-onPrimary text-sm font-semibold px-lg py-sm rounded-full shadow-sm hover:bg-primaryContainer transition-colors inline-flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">tune</span>
                <span>Adjust filters</span>
              </button>
            </div>
          </section>
        )}

        {/* ERROR STATE */}
        {state === "error" && (
          <section className="bg-errorContainer/20 border border-outlineVariant rounded-xl p-lg md:p-xl flex flex-col items-center justify-center text-center min-h-[350px] shadow-sm relative animate-fade-in">
            <div className="w-16 h-16 bg-errorContainer text-onError rounded-full flex items-center justify-center mb-md shadow-sm">
              <span className="material-symbols-outlined text-3xl">error</span>
            </div>
            <h2 className="font-titleMd text-titleMd text-onError mb-sm">
              Something went wrong
            </h2>
            <p className="font-bodyLg text-bodyLg text-onSurfaceVariant max-w-md mb-lg">
              {errorDetails || "We're having trouble connecting to the server. Please check your connection and try again."}
            </p>
            <button
              onClick={() => setState("home")}
              className="bg-surface border-2 border-primary text-primary text-sm font-semibold px-lg py-sm rounded-full shadow-sm hover:bg-surfaceContainerLow transition-colors inline-flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">refresh</span>
              <span>Retry</span>
            </button>
          </section>
        )}

      </main>

      {/* BottomNavBar (Mobile Only) */}
      <nav className="md:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-md py-base bg-surfaceContainer dark:bg-surfaceContainerHighest shadow-lg rounded-t-xl">
        <button
          onClick={() => setState("home")}
          className={`flex flex-col items-center justify-center rounded-full px-4 py-1 hover:opacity-85 transition-all duration-200 ${
            state === "home" ? "bg-secondaryContainer text-onSecondaryContainer" : "text-onSurfaceVariant"
          }`}
        >
          <span className="material-symbols-outlined">explore</span>
          <span className="font-labelMd text-labelMd mt-1">Explore</span>
        </button>
        <button
          className="flex flex-col items-center justify-center text-onSurfaceVariant px-4 py-1 hover:opacity-85 transition-opacity"
          onClick={() => alert(`Saved Bookmarks: ${bookmarkedIds.length} restaurant(s) saved.`)}
        >
          <span className="material-symbols-outlined">bookmark</span>
          <span className="font-labelMd text-labelMd mt-1">Saved</span>
        </button>
        <button
          className="flex flex-col items-center justify-center text-onSurfaceVariant px-4 py-1 hover:opacity-85 transition-opacity"
          onClick={() => alert("History feature coming soon!")}
        >
          <span className="material-symbols-outlined">history</span>
          <span className="font-labelMd text-labelMd mt-1">History</span>
        </button>
        <button
          className="flex flex-col items-center justify-center text-onSurfaceVariant px-4 py-1 hover:opacity-85 transition-opacity"
          onClick={() => alert("Profile options coming soon!")}
        >
          <span className="material-symbols-outlined">person</span>
          <span className="font-labelMd text-labelMd mt-1">Profile</span>
        </button>
      </nav>
    </div>
  );
}
