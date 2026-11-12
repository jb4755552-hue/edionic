/* Edionic Web Editor UI Logic (app.js)
   - Works identically whether opened via http://127.0.0.1:8080 or directly from C:\ai editing\frontend\index.html
   - View 1 (#view-landing-hub): Clean Landing Page + Ready-Made & Custom 9:16 Style Creator
   - View 2 (#view-nle-studio): Full-Screen InVideo-Style NLE Workspace (Agent Sidebar, Source, Program Monitor, Inspector, Media Bin, Timeline + dB Meter)
   - Sections 5, 6, 7 run quietly in the backend without cluttering the front UI.
*/

const API_BASE =
  window.location.protocol === "file:" ? "http://127.0.0.1:8080" : "";

const state = {
  theme: localStorage.getItem("edionic_theme") || "dark",
  active_view: "landing", // "landing" | "nle"
  version: 1,
  caption_preset: "glow",
  title_text: "Edionic 9:16 Hook Title",
  style_preset: "smoke2_style",
  selected_style_card: "tour",
  template_id: null,
  sfx: [
    { name: "whoosh", placed_at_s: 1.0 },
    { name: "pop", placed_at_s: 2.5 },
    { name: "ding", placed_at_s: 4.0 },
    { name: "thump", placed_at_s: 5.5 },
    { name: "snap", placed_at_s: 7.0 }
  ],
  storyboard: {
    title: "Test plan",
    // Empty by default (Batch 4): the old hardcoded b0/b1 placeholder
    // blocks made the backend believe every job had manual graphics, so
    // the motion planner never ran on the default flow. The planner now
    // plans from the transcript; the user adds blocks only when authoring.
    blocks: []
  },
  edl: null
};

const STYLE_CARDS_CATALOG = [
  {
    id: "tour",
    name: "Tour",
    kicker: "how to",
    headline: "STUDY SMARTER",
    headlineColor: "#FACC15",
    bgGradient: "linear-gradient(165deg, #422006 0%, #1C1917 60%, #090D16 100%)",
    category: ["all", "bold"],
    caption_preset: "glow",
    style_preset: "smoke2_style",
    tag: "glow · Warm Amber"
  },
  {
    id: "strategist",
    name: "Strategist",
    kicker: "USE AI TO",
    headline: "LEARN",
    headlineColor: "#FFFFFF",
    bgGradient: "linear-gradient(165deg, #450A0A 0%, #1E1B4B 65%, #090D16 100%)",
    category: ["all", "bold"],
    caption_preset: "condensed",
    style_preset: "smoke2_style",
    tag: "condensed · High Impact"
  },
  {
    id: "cozy",
    name: "Cozy",
    kicker: "my sunday",
    headline: "reset",
    headlineColor: "#F472B6",
    bgGradient: "linear-gradient(165deg, #831843 0%, #31102F 60%, #0F172A 100%)",
    category: ["all", "new", "polished"],
    caption_preset: "handwritten",
    style_preset: "smoke2_style",
    tag: "handwritten · Soft Script"
  },
  {
    id: "vox_style",
    name: "Vox-Style",
    kicker: "THE DAY OF",
    headline: "Two Noons",
    headlineColor: "#38BDF8",
    bgGradient: "linear-gradient(165deg, #0F172A 0%, #1E293B 55%, #090D16 100%)",
    category: ["all", "polished"],
    caption_preset: "pill_highlight",
    style_preset: "smoke2_style",
    tag: "pill_highlight · Explainer"
  },
  {
    id: "clients_hook",
    name: "still no clients?",
    kicker: "agency growth",
    headline: "CLIENTS?",
    headlineColor: "#FB923C",
    bgGradient: "linear-gradient(165deg, #431407 0%, #18181B 65%, #09090B 100%)",
    category: ["all", "new", "minimal"],
    caption_preset: "karaoke_pop",
    style_preset: "smoke2_style",
    tag: "karaoke_pop · Active Word"
  },
  {
    id: "sold_real_estate",
    name: "Open House",
    kicker: "JUST LISTED",
    headline: "SOLD",
    headlineColor: "#93C5FD",
    bgGradient: "linear-gradient(165deg, #1E3A8A 0%, #172554 60%, #090D16 100%)",
    category: ["all", "polished", "bold"],
    caption_preset: "extrude_3d",
    style_preset: "smoke2_style",
    tag: "extrude_3d · 3D Shadow"
  },
  {
    id: "aura_mono",
    name: "Aura",
    kicker: "MINDSET",
    headline: "AURA",
    headlineColor: "#EF4444",
    bgGradient: "linear-gradient(165deg, #27272A 0%, #18181B 55%, #09090B 100%)",
    category: ["all", "minimal"],
    caption_preset: "neon_serif",
    style_preset: "smoke2_style",
    tag: "neon_serif · Dark Mono"
  },
  {
    id: "bulletin_pod",
    name: "Bulletin",
    kicker: "Save more",
    headline: "penalties",
    headlineColor: "#FFFFFF",
    bgGradient: "linear-gradient(165deg, #7C2D12 0%, #111827 60%, #090D16 100%)",
    category: ["all", "new", "polished"],
    caption_preset: "podcast_two_tier",
    style_preset: "smoke2_style",
    tag: "podcast_two_tier · Clip"
  },
  {
    id: "sweep_hook",
    name: "Light Sweep",
    kicker: "0.0s - 2.5s",
    headline: "SWEEP HOOK",
    headlineColor: "#67E8F9",
    bgGradient: "linear-gradient(165deg, #0E7490 0%, #1E1B4B 60%, #090D16 100%)",
    category: ["all", "new", "bold"],
    caption_preset: "light_sweep_title",
    style_preset: "smoke2_style",
    tag: "light_sweep_title · Hook"
  },
  {
    id: "gradient_flow",
    name: "Prism Steps",
    kicker: "COLOR STEP",
    headline: "GRADIENT",
    headlineColor: "#34D399",
    bgGradient: "linear-gradient(165deg, #065F46 0%, #1E1B4B 65%, #090D16 100%)",
    category: ["all", "bold"],
    caption_preset: "gradient_steps",
    style_preset: "smoke2_style",
    tag: "gradient_steps · Word Color"
  },
  {
    id: "minimal_pro",
    name: "Minimal Clean",
    kicker: "CLEAN SUBS",
    headline: "MINIMAL",
    headlineColor: "#F8FAFC",
    bgGradient: "linear-gradient(165deg, #334155 0%, #0F172A 65%, #090D16 100%)",
    category: ["all", "minimal"],
    caption_preset: "minimal_clean",
    style_preset: "smoke2_style",
    tag: "minimal_clean · Crisp"
  },
  {
    id: "archival_serif",
    name: "Archival Serif",
    kicker: "DOCUMENTARY",
    headline: "ARCHIVE",
    headlineColor: "#F5F0E6",
    bgGradient: "linear-gradient(165deg, #292524 0%, #1C1917 60%, #090D16 100%)",
    category: ["all", "polished"],
    caption_preset: "serif_title",
    style_preset: "smoke2_style",
    tag: "serif_title · Title Card"
  },
  {
    id: "tpl_saas_dark_premium",
    name: "SaaS Dark Premium",
    kicker: "MOTION EXPLAINER",
    headline: "DARK",
    headlineColor: "#60A5FA",
    bgGradient: "linear-gradient(165deg, #0B1020 0%, #000000 60%, #090D16 100%)",
    category: ["all", "templates", "bold"],
    caption_preset: "minimal_clean",
    style_preset: "neon_aura_style",
    tag: "Template · minimal_clean",
    template_id: "saas_dark_premium",
    template_title_text: "Your product name + one-line claim",
    sfx_defaults: [
      { name: "swish", placed_at_s: 1.0 },
      { name: "swish", placed_at_s: 5.0 },
      { name: "swish", placed_at_s: 9.0 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Brand mark + swoosh in the first 3 seconds, then logo, product UI, eclipse logo.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame",
        graphic: "Title card",
        sfx: "swish"
      }
    ]
  },
  {
    id: "tpl_saas_clean_flat",
    name: "SaaS Clean Flat",
    kicker: "MOTION EXPLAINER",
    headline: "CLEAN",
    headlineColor: "#2F5BFF",
    bgGradient: "linear-gradient(165deg, #F5F6F8 0%, #E8EDFF 55%, #C7D2FE 100%)",
    category: ["all", "templates", "minimal"],
    caption_preset: "minimal_clean",
    style_preset: "clean_tech_style",
    tag: "Template · minimal_clean",
    template_id: "saas_clean_flat",
    template_title_text: "Your brand name (end card)",
    sfx_defaults: [
      { name: "pop", placed_at_s: 1.0 },
      { name: "pop", placed_at_s: 2.5 },
      { name: "pop", placed_at_s: 4.0 },
      { name: "ding", placed_at_s: 8.0 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Problem list in the first 3 seconds, then the automatic turn, then a Coming soon brand card.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame",
        graphic: "Title card",
        sfx: "pop"
      }
    ]
  },
  {
    id: "tpl_talking_head_pro",
    name: "Talking Head Pro",
    kicker: "BOLD CAPTIONS",
    headline: "PROOF",
    headlineColor: "#22C55E",
    bgGradient: "linear-gradient(165deg, #14532D 0%, #111111 60%, #090D16 100%)",
    category: ["all", "templates", "bold"],
    caption_preset: "condensed",
    style_preset: "creator_motion_graphics_style",
    tag: "Template · condensed",
    template_id: "talking_head_pro",
    template_title_text: "Your big claim (first 3 seconds)",
    sfx_defaults: [
      { name: "pop", placed_at_s: 1.0 },
      { name: "snap", placed_at_s: 2.5 },
      { name: "pop", placed_at_s: 4.0 },
      { name: "whoosh", placed_at_s: 5.5 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "One big claim in the first 3 seconds (title card + face, no clutter), then proof, steps, CTA.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame",
        graphic: "Title card",
        sfx: "pop"
      }
    ]
  },
  {
    id: "tpl_trust_talking_head",
    name: "Trust Talking Head",
    kicker: "SLOW SINGLE TAKE",
    headline: "TRUST",
    headlineColor: "#1F2937",
    bgGradient: "linear-gradient(165deg, #F8F5F0 0%, #E8E0D4 55%, #D6CDBF 100%)",
    category: ["all", "templates", "polished"],
    caption_preset: "minimal_clean",
    style_preset: "warm_canvas_style",
    tag: "Template · minimal_clean",
    template_id: "trust_talking_head",
    template_title_text: "Your value statement",
    sfx_defaults: [],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Open on the value statement, then values, credentials, services, character argument, soft invitation. No cuts.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame",
        graphic: "Title card",
        sfx: ""
      }
    ]
  },
  {
    id: "tpl_split_screen_breakdown",
    name: "Split-Screen Breakdown",
    kicker: "BEFORE / AFTER",
    headline: "VS",
    headlineColor: "#FACC15",
    bgGradient: "linear-gradient(165deg, #0A0A0A 0%, #262626 55%, #090D16 100%)",
    category: ["all", "templates", "bold"],
    caption_preset: "condensed",
    style_preset: "creator_motion_graphics_style",
    tag: "Template · condensed",
    template_id: "split_screen_breakdown",
    template_title_text: "Your contrast claim",
    sfx_defaults: [
      { name: "pop", placed_at_s: 1.0 },
      { name: "click", placed_at_s: 2.0 },
      { name: "pop", placed_at_s: 3.5 },
      { name: "click", placed_at_s: 5.0 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Contrast claim in the first 3 seconds, then proof by comparison, then verdict.",
        start: 0.0,
        end: 3.0,
        visual: "split_50_50_stack",
        graphic: "Title card",
        sfx: "pop"
      }
    ]
  },
  {
    id: "tpl_screen_record_tutorial",
    name: "Screen-Record Tutorial",
    kicker: "CRAFT TIP",
    headline: "TIMELINE",
    headlineColor: "#4F9CF0",
    bgGradient: "linear-gradient(165deg, #14141F 0%, #26263A 60%, #090D16 100%)",
    category: ["all", "templates", "minimal"],
    caption_preset: "minimal_clean",
    style_preset: "software_walkthrough_style",
    tag: "Template · minimal_clean",
    template_id: "screen_record_tutorial",
    template_title_text: "Your tutorial question",
    sfx_defaults: [
      { name: "click", placed_at_s: 1.0 },
      { name: "click", placed_at_s: 2.5 },
      { name: "click", placed_at_s: 4.0 },
      { name: "riser", placed_at_s: 6.0 },
      { name: "whoosh", placed_at_s: 7.0 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "The question is the hook, then steps, then payoff.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame",
        graphic: "Title card",
        sfx: "click"
      }
    ]
  },
  {
    id: "tpl_archival_documentary",
    name: "Archival Documentary",
    kicker: "CINEMATIC ESSAY",
    headline: "HISTORY",
    headlineColor: "#F5F0E6",
    bgGradient: "linear-gradient(165deg, #57534E 0%, #292524 60%, #090D16 100%)",
    category: ["all", "templates", "polished"],
    caption_preset: "serif_title",
    style_preset: "smoke2_style",
    tag: "Template · serif_title",
    template_id: "archival_documentary",
    template_title_text: "YOUR TITLE IN SERIF CAPS",
    sfx_defaults: [
      { name: "swish", placed_at_s: 1.0 },
      { name: "swish", placed_at_s: 7.0 },
      { name: "swish", placed_at_s: 13.0 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Huge image + serif title card in the first 3 seconds, then fact, implication, punchline.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame",
        graphic: "Title card",
        sfx: "swish"
      }
    ]
  },
  {
    id: "tpl_portfolio_showreel",
    name: "Portfolio Showreel",
    kicker: "KINETIC TYPE",
    headline: "PORTFOLIO",
    headlineColor: "#A3E635",
    bgGradient: "linear-gradient(165deg, #1A2E05 0%, #0A0A0A 60%, #090D16 100%)",
    category: ["all", "templates", "bold"],
    caption_preset: "condensed",
    style_preset: "creator_motion_graphics_style",
    tag: "Template · condensed",
    template_id: "portfolio_showreel",
    template_title_text: "PORTFOLIO",
    sfx_defaults: [
      { name: "thump", placed_at_s: 1.0 },
      { name: "whoosh", placed_at_s: 2.0 },
      { name: "thump", placed_at_s: 5.0 },
      { name: "whoosh", placed_at_s: 8.0 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Giant kinetic-type title in the first 3 seconds, then the work grid proves range.",
        start: 0.0,
        end: 3.0,
        visual: "vertical_stack_grid",
        graphic: "Title card",
        sfx: "thump"
      }
    ]
  },
  {
    id: "tpl_ai_showcase_desk",
    name: "AI Showcase Desk",
    kicker: "DESK REVEAL",
    headline: "REVEAL",
    headlineColor: "#FF8A3D",
    bgGradient: "linear-gradient(165deg, #1F2937 0%, #0F1115 60%, #090D16 100%)",
    category: ["all", "templates", "polished"],
    caption_preset: "condensed",
    style_preset: "neon_aura_style",
    tag: "Template · condensed",
    template_id: "ai_showcase_desk",
    template_title_text: "Your AI demo claim",
    sfx_defaults: [
      { name: "swish", placed_at_s: 1.0 },
      { name: "swish", placed_at_s: 6.0 },
      { name: "swish", placed_at_s: 11.0 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Desk + bold claim title in the first 3 seconds, then proof-by-demo on the monitor, then end screen.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame",
        graphic: "Title card",
        sfx: "swish"
      }
    ]
  },
  {
    id: "tpl_local_language_demo",
    name: "Local-Language Demo",
    kicker: "ROMAN URDU · HINGLISH",
    headline: "REVIEW",
    headlineColor: "#FACC15",
    bgGradient: "linear-gradient(165deg, #1E3A8A 0%, #111827 60%, #090D16 100%)",
    category: ["all", "templates", "new"],
    caption_preset: "pill_highlight",
    style_preset: "vox_explainer_style",
    tag: "Template · pill_highlight",
    template_id: "local_language_demo",
    template_title_text: "Your product verdict line",
    sfx_defaults: [
      { name: "pop", placed_at_s: 1.0 },
      { name: "pop", placed_at_s: 2.5 },
      { name: "pop", placed_at_s: 4.0 },
      { name: "snap", placed_at_s: 5.5 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Product on face or a fear hook in the first 3 seconds, then demo/proof, then verdict/CTA.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame",
        graphic: "Title card",
        sfx: "pop"
      }
    ]
  },
  {
    id: "tpl_gaming_montage",
    name: "Gaming Montage",
    kicker: "PUBG MOBILE TDM",
    headline: "KILLS",
    headlineColor: "#EF4444",
    bgGradient: "linear-gradient(165deg, #450A0A 0%, #14181F 60%, #090D16 100%)",
    category: ["all", "templates", "bold"],
    caption_preset: "minimal_clean",
    style_preset: "neon_aura_style",
    tag: "Template · minimal_clean",
    template_id: "gaming_montage",
    template_title_text: "Your player tag",
    sfx_defaults: [
      { name: "thump", placed_at_s: 1.0 },
      { name: "thump", placed_at_s: 3.0 },
      { name: "thump", placed_at_s: 5.0 },
      { name: "riser", placed_at_s: 6.5 },
      { name: "whoosh", placed_at_s: 7.5 }
    ],
    storyboard_hook: [
      {
        id: "b0",
        title: "hook",
        text: "Immediate action, no intro card: open on the first kill with HUD visible. Streak badges are the proof beats.",
        start: 0.0,
        end: 3.0,
        visual: "full_frame_centre_crop",
        graphic: "Title card",
        sfx: "thump"
      }
    ]
  }
];

/* =========================================================================
   VIEW SWITCHER: LANDING HUB <-> FULL-SCREEN NLE TIMELINE STUDIO
   ========================================================================= */
function switchScreenView(targetView) {
  state.active_view = targetView;
  const landingEl = document.getElementById("view-landing-hub");
  const nleEl = document.getElementById("view-nle-studio");

  if (targetView === "nle") {
    if (landingEl) landingEl.style.display = "none";
    if (nleEl) nleEl.style.display = "block";
    document.body.className = "mode-studio";
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else {
    if (nleEl) nleEl.style.display = "none";
    if (landingEl) landingEl.style.display = "block";
    document.body.className = "mode-landing";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

/* =========================================================================
   DARK / LIGHT THEME SWITCHER
   ========================================================================= */
function applyTheme(themeName) {
  state.theme = themeName === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", state.theme);
  localStorage.setItem("edionic_theme", state.theme);

  document.querySelectorAll(".theme-icon").forEach((el) => {
    el.textContent = state.theme === "dark" ? "☀️" : "🌙";
  });
  document.querySelectorAll(".theme-label").forEach((el) => {
    el.textContent = state.theme === "dark" ? "Light Mode" : "Dark Mode";
  });
}

/* =========================================================================
   LOGGING & CONVERSATIONAL AGENT CHAT BUBBLES
   ========================================================================= */
function appendLog(msg) {
  const box = document.getElementById("agent-log-box");
  if (!box) return;
  const ts = new Date().toLocaleTimeString();
  box.textContent += `\n[${ts}] ${msg}`;
}

function appendAgentChatBubble(sender, text, isUser = false) {
  const thread = document.getElementById("agent-chat-thread");
  if (!thread) return;
  const wrap = document.createElement("div");
  wrap.className = `agent-msg ${isUser ? "agent-msg-user" : "agent-msg-bot"}`;
  wrap.innerHTML = `
    <div class="agent-msg-sender">${sender}</div>
    <div class="agent-msg-bubble">${text}</div>
  `;
  thread.appendChild(wrap);
  thread.scrollTop = thread.scrollHeight;
}

/* =========================================================================
   STYLE CARDS & CUSTOM TEMPLATE CREATOR
   ========================================================================= */
function renderVisualStyleCards(filterCat = "all", searchQuery = "") {
  const grid = document.getElementById("visual-styles-grid");
  if (!grid) return;
  grid.innerHTML = "";

  const q = searchQuery.trim().toLowerCase();
  const filtered = STYLE_CARDS_CATALOG.filter((card) => {
    const matchesCat = filterCat === "all" || card.category.includes(filterCat);
    const matchesSearch =
      !q ||
      card.name.toLowerCase().includes(q) ||
      card.headline.toLowerCase().includes(q) ||
      card.caption_preset.toLowerCase().includes(q) ||
      card.tag.toLowerCase().includes(q);
    return matchesCat && matchesSearch;
  });

  filtered.forEach((card) => {
    const el = document.createElement("div");
    el.className = `style-card-916 ${state.selected_style_card === card.id ? "selected" : ""}`;
    el.style.background = card.bgGradient;
    el.innerHTML = `
      <div class="style-card-top">
        <div class="style-card-kicker">${card.kicker}</div>
        <div class="style-card-headline" style="color:${card.headlineColor};">${card.headline}</div>
      </div>
      <div class="style-card-avatar">
        <div class="avatar-head"></div>
        <div class="avatar-shoulders"></div>
      </div>
      <div class="style-card-bottom">
        <div class="style-card-name">${card.name}</div>
        <div class="style-card-preset-tag">${card.tag}</div>
      </div>
    `;
    el.addEventListener("click", () => {
      // User clicked a style card -> Apply style & immediately open full-screen NLE Timeline!
      applyStyleCardSelection(card, true);
    });
    grid.appendChild(el);
  });
}

function applyStyleCardSelection(card, openNleImmediately = false) {
  state.selected_style_card = card.id;
  state.caption_preset = card.caption_preset;
  state.style_preset = card.style_preset || "smoke2_style";
  state.template_id = card.template_id || null;

  // Template cards fill the job with their bundle: SFX defaults, storyboard
  // hook block and title text. Plain style cards leave those untouched.
  if (card.template_id) {
    if (Array.isArray(card.sfx_defaults)) {
      state.sfx = JSON.parse(JSON.stringify(card.sfx_defaults));
    }
    if (Array.isArray(card.storyboard_hook)) {
      state.storyboard = {
        title: card.name,
        blocks: JSON.parse(JSON.stringify(card.storyboard_hook))
      };
    }
    if (card.template_title_text) {
      state.title_text = card.template_title_text;
    }
  }

  document.querySelectorAll(".cap-chip").forEach((c) => {
    c.classList.toggle("active", c.getAttribute("data-preset") === state.caption_preset);
  });
  const titleWrap = document.getElementById("light-sweep-title-wrap");
  if (titleWrap) {
    titleWrap.style.display = state.caption_preset === "light_sweep_title" ? "block" : "none";
  }

  const ccClip = document.getElementById("timeline-cc-clip");
  if (ccClip) {
    ccClip.textContent = `Preset: ${state.caption_preset} (Word-Level Timestamps · ${card.name})`;
  }
  const activeStylePill = document.getElementById("active-style-pill");
  if (activeStylePill) {
    activeStylePill.textContent = `Style: ${card.name} (${state.caption_preset})`;
  }
  const inspCode = document.getElementById("inspector-style-code");
  if (inspCode) {
    inspCode.textContent = state.style_preset;
  }

  renderVisualStyleCards();
  syncEdlInspector();
  appendLog(`Selected Style Template "${card.name}" -> caption_preset=${state.caption_preset}`);
  appendAgentChatBubble(
    "Edionic AI",
    `Hey Creator, <strong>${card.name}</strong> style is active (Caption preset: <code>${state.caption_preset}</code>). How should we refine your timeline?`
  );

  if (openNleImmediately) {
    switchScreenView("nle");
  }
}

/* =========================================================================
   SFX, STORYBOARD, TRANSCRIPT & BACKEND EDL SYNC
   ========================================================================= */
function renderSfxList() {
  const container = document.getElementById("sfx-placements-list");
  if (!container) return;
  container.innerHTML = "";
  state.sfx.forEach((item, idx) => {
    const row = document.createElement("div");
    row.style.cssText =
      "display:flex;justify-content:space-between;align-items:center;background:var(--bg-input);padding:5px 8px;border:1px solid var(--border);border-radius:5px;";
    row.innerHTML = `
      <span><strong>#${idx + 1} ${item.name}</strong></span>
      <span class="nle-meta-tag">@ ${item.placed_at_s.toFixed(1)}s (−12 dB)</span>
    `;
    container.appendChild(row);
  });
}

function renderStoryboardBlocks() {
  const container = document.getElementById("storyboard-blocks-container");
  if (!container) return;
  container.innerHTML = "";
  state.storyboard.blocks.forEach((blk, idx) => {
    const card = document.createElement("div");
    card.style.cssText =
      "background:var(--bg-input);padding:8px;border:1px solid var(--border);border-radius:6px;font-size:11.5px;";
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;font-weight:700;margin-bottom:4px;">
        <span>Block ${blk.id} (${blk.start.toFixed(1)}s–${blk.end.toFixed(1)}s)</span>
        <span style="color:var(--accent);">SFX: ${blk.sfx}</span>
      </div>
      <input class="input-box sb-text-input" data-idx="${idx}" value="${blk.text}" style="margin-bottom:4px;" />
      <div style="font-size:10.5px;color:var(--text-secondary);">${blk.visual} · ${blk.graphic}</div>
    `;
    container.appendChild(card);
  });

  container.querySelectorAll(".sb-text-input").forEach((inp) => {
    inp.addEventListener("input", (e) => {
      const i = parseInt(e.target.getAttribute("data-idx"), 10);
      state.storyboard.blocks[i].text = e.target.value;
      syncEdlInspector();
    });
  });
}

function renderTranscriptWords(customWords = null) {
  const box = document.getElementById("live-transcript-box");
  const countBadge = document.getElementById("transcript-word-count");
  if (!box) return;

  let words = Array.isArray(customWords) ? customWords : [];
  if (!words.length && state.edl && Array.isArray(state.edl.tracks)) {
    const ccTrack = state.edl.tracks.find((t) => t.id === "CC");
    if (ccTrack && Array.isArray(ccTrack.clips)) {
      words = ccTrack.clips;
    }
  }
  if (!words.length) {
    words = [
      { word: "Welcome", start: 0.0 },
      { word: "to", start: 0.46 },
      { word: "Edionic", start: 0.8 },
      { word: "Vertical", start: 1.22 },
      { word: "Video", start: 1.66 },
      { word: "Editor.", start: 2.1 },
      { word: "AI", start: 2.57 },
      { word: "cuts", start: 2.81 },
      { word: "silence", start: 3.07 },
      { word: "and", start: 3.43 },
      { word: "builds", start: 3.75 },
      { word: "glowing", start: 4.01 },
      { word: "captions.", start: 4.39 }
    ];
  }

  if (countBadge) {
    countBadge.textContent = `${words.length}`;
  }

  box.innerHTML = "";
  words.forEach((w) => {
    const span = document.createElement("span");
    span.className = "transcript-word-pill";
    const s = typeof w.start === "number" ? w.start.toFixed(2) : "0.00";
    span.innerHTML = `${w.word}<small>${s}s</small>`;
    span.addEventListener("click", () => {
      const vid = document.getElementById("preview-video");
      if (vid && typeof w.start === "number") {
        vid.currentTime = w.start;
      }
    });
    box.appendChild(span);
  });
}

function buildExportJobPayload() {
  return {
    version: 1,
    caption_preset: state.caption_preset,
    title_text: state.title_text,
    style_preset: state.style_preset,
    sfx: state.sfx,
    storyboard: state.storyboard
  };
}

function syncEdlInspector() {
  const inspector = document.getElementById("edl-inspector");
  if (!inspector) return;
  const displayObj = state.edl || buildExportJobPayload();
  displayObj.caption_preset = state.caption_preset;
  displayObj.title_text = state.title_text;
  displayObj.style_preset = state.style_preset;
  displayObj.sfx = state.sfx;
  displayObj.storyboard = state.storyboard;
  inspector.value = JSON.stringify(displayObj, null, 2);
}

/* =========================================================================
   BACKEND API INTEGRATION (Works from both http://127.0.0.1:8080 and file://)
   ========================================================================= */
async function fetchStatusAndEdl() {
  try {
    const [stRes, edlRes] = await Promise.all([
      fetch(`${API_BASE}/api/status`),
      fetch(`${API_BASE}/api/edl`)
    ]);
    if (stRes.ok) {
      const st = await stRes.json();
      const badge = document.getElementById("engine-badge");
      if (badge && st.media_engine) {
        const ff = st.media_engine.ffmpeg_available ? "FFmpeg OK" : "FFmpeg Missing";
        const wh = st.media_engine.faster_whisper_available ? "Whisper OK" : "Whisper Pending";
        badge.textContent = `${ff} · ${wh}`;
      }
      const brainBadge = document.getElementById("brain-route-badge");
      if (brainBadge && st.brain_router) {
        brainBadge.textContent = st.brain_router.active_primary;
      }
    }
    if (edlRes.ok) {
      state.edl = await edlRes.json();
      syncEdlInspector();
      renderTranscriptWords();
    }
  } catch (err) {
    appendLog(`Backend status note: ${err.message}`);
  }
}

async function handleClipUpload(file) {
  if (!file) return;
  const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
  appendLog(`Uploading raw clip: ${file.name} (${sizeMB} MB)...`);
  const hubStatus = document.getElementById("hub-upload-status");
  const binStatus = document.getElementById("mediabin-status-text");

  // 1. Instant Zero-Wait Local Preview in 9:16 Monitor before/during upload!
  const localBlobUrl = URL.createObjectURL(file);
  const videoEl = document.getElementById("preview-video");
  if (videoEl) {
    videoEl.src = localBlobUrl;
  }

  // 2. High-speed XHR Upload with Live Percentage Progress
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/upload`, true);
    xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name));

    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable) {
        const pct = Math.round((evt.loaded / evt.total) * 100);
        if (hubStatus) hubStatus.textContent = `⚡ Uploading ${file.name}: ${pct}% (${sizeMB} MB)...`;
        if (binStatus) binStatus.textContent = `⚡ Uploading ${file.name}: ${pct}%...`;
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          state.edl = data.edl;
          syncEdlInspector();
          renderTranscriptWords();
          const v1Lane = document.getElementById("timeline-v1-lane");
          if (v1Lane) {
            const durLabel = data.duration_s ? `${data.duration_s}s` : "Full Clip";
            v1Lane.innerHTML = `<span class="track-clip">${data.filename} (in: 0.0s, out: ${durLabel}, speed: 1.0x)</span>`;
          }
          if (videoEl) {
            videoEl.src = `${API_BASE}${data.media_url}`;
          }
          if (hubStatus) {
            hubStatus.textContent = `✓ Loaded: ${data.filename} (${sizeMB} MB) — Now click any Style Card below!`;
          }
          if (binStatus) {
            binStatus.textContent = `✓ Media Loaded: ${data.filename} (${sizeMB} MB)`;
          }
          appendAgentChatBubble("Edionic AI", `Uploaded <code>${data.filename}</code> (${sizeMB} MB) onto Main Timeline (V1/A1).`);
        } catch (err) {
          appendLog(`Upload parse note: ${err.message}`);
        }
      } else {
        if (hubStatus) hubStatus.textContent = `Upload failed (HTTP ${xhr.status})`;
      }
      resolve();
    };

    xhr.onerror = () => {
      if (hubStatus) hubStatus.textContent = `Upload error — check server connection`;
      resolve();
    };

    xhr.send(file);
  });
}

async function triggerRenderJob() {
  const statusText = document.getElementById("job-status-text");
  const pctText = document.getElementById("job-pct-text");
  const fill = document.getElementById("job-progress-fill");
  const qaBox = document.getElementById("slop-gate-results");
  const dlBtn = document.getElementById("btn-download-render");

  if (statusText) statusText.textContent = "Queueing render...";
  if (pctText) pctText.textContent = "5%";
  if (fill) fill.style.width = "5%";
  if (qaBox) qaBox.innerHTML = "";

  try {
    const edlPayload = Object.assign({}, state.edl || {}, {
      caption_preset: state.caption_preset,
      title_text: state.title_text,
      style_preset: state.style_preset,
      sfx: state.sfx,
      storyboard: state.storyboard,
      template_id: state.template_id
    });
    const res = await fetch(`${API_BASE}/api/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ edl: edlPayload })
    });
    const job = await res.json();
    appendAgentChatBubble(
      "Edionic AI",
      `Rendering 9:16 video (Job <code>${job.job_id.slice(0, 8)}</code>, preset: <code>${state.caption_preset}</code>)...`
    );

    const poll = setInterval(async () => {
      const jRes = await fetch(`${API_BASE}/api/jobs/${job.job_id}`);
      if (!jRes.ok) return;
      const jData = await jRes.json();
      if (statusText) statusText.textContent = jData.message || jData.status;
      if (pctText) pctText.textContent = `${jData.progress || 0}%`;
      if (fill) fill.style.width = `${jData.progress || 0}%`;

      if (jData.status === "completed" || jData.status === "qa_failed" || jData.status === "failed") {
        clearInterval(poll);
        if (jData.download_url) {
          const fullUrl = `${API_BASE}${jData.download_url}`;
          const videoEl = document.getElementById("preview-video");
          if (videoEl) {
            videoEl.src = `${fullUrl}?t=${Date.now()}`;
            videoEl.play().catch(() => {});
          }
          if (dlBtn) {
            dlBtn.href = fullUrl;
            dlBtn.style.display = "inline-flex";
          }
          if (jData.render_info?.transcription_words) {
            renderTranscriptWords(jData.render_info.transcription_words);
          }
          appendAgentChatBubble(
            "Edionic AI",
            `✅ Render finished in ${jData.render_info?.elapsed_s || 0}s! Playing edited 9:16 video with burned captions &amp; cuts in the Preview Monitor.`
          );
        }
        if (jData.qa_report && jData.qa_report.checks && qaBox) {
          qaBox.innerHTML = "";
          jData.qa_report.checks.forEach((chk) => {
            const span = document.createElement("span");
            span.className = `qa-badge ${chk.pass ? "qa-pass" : "qa-unverified"}`;
            span.textContent = `${chk.pass ? "PASS" : "FAIL"}: ${chk.name}`;
            qaBox.appendChild(span);
          });
        }
      }
    }, 600);
  } catch (err) {
    if (statusText) statusText.textContent = `Render error: ${err.message}`;
  }
}

/* =========================================================================
   DOM INITIALIZATION
   ========================================================================= */
document.addEventListener("DOMContentLoaded", () => {
  applyTheme(state.theme);
  renderVisualStyleCards();
  renderSfxList();
  renderStoryboardBlocks();
  renderTranscriptWords();
  syncEdlInspector();
  fetchStatusAndEdl();

  // Theme Toggle Buttons (in both Landing and NLE headers)
  document.querySelectorAll(".btn-theme-switch").forEach((btn) => {
    btn.addEventListener("click", () => {
      applyTheme(state.theme === "dark" ? "light" : "dark");
    });
  });

  // View Navigation Buttons (Landing <-> Full-Screen NLE Studio)
  const btnNavOpenNle = document.getElementById("btn-nav-open-nle");
  const btnHeroOpenNle = document.getElementById("btn-hero-open-nle");
  const btnBackToLanding = document.getElementById("btn-back-to-landing");

  if (btnNavOpenNle) btnNavOpenNle.addEventListener("click", () => switchScreenView("nle"));
  if (btnHeroOpenNle) btnHeroOpenNle.addEventListener("click", () => switchScreenView("nle"));
  if (btnBackToLanding) btnBackToLanding.addEventListener("click", () => switchScreenView("landing"));

  // Custom Style Creator Drawer
  const btnToggleCreator = document.getElementById("btn-toggle-custom-creator");
  const btnCloseCreator = document.getElementById("btn-close-custom-creator");
  const creatorDrawer = document.getElementById("custom-style-creator-drawer");

  if (btnToggleCreator && creatorDrawer) {
    btnToggleCreator.addEventListener("click", () => {
      creatorDrawer.style.display = creatorDrawer.style.display === "none" ? "block" : "none";
    });
  }
  if (btnCloseCreator && creatorDrawer) {
    btnCloseCreator.addEventListener("click", () => {
      creatorDrawer.style.display = "none";
    });
  }

  // Save Custom Style -> Add to Catalog & Immediately Open NLE Timeline!
  const btnSaveCustomStyle = document.getElementById("btn-save-custom-style");
  if (btnSaveCustomStyle) {
    btnSaveCustomStyle.addEventListener("click", () => {
      const nameVal = document.getElementById("custom-style-name").value.trim() || "Custom 9:16 Style";
      const capPreset = document.getElementById("custom-style-caption").value;
      const accentHex = document.getElementById("custom-style-color").value;
      const tagVal = document.getElementById("custom-style-tag").value.trim() || "Custom Template";

      const newCard = {
        id: `custom_${Date.now()}`,
        name: nameVal,
        kicker: "CUSTOM STYLE",
        headline: nameVal.split(" ").slice(0, 2).join(" ").toUpperCase(),
        headlineColor: accentHex,
        bgGradient: `linear-gradient(165deg, ${accentHex}55 0%, #141824 65%, #090D16 100%)`,
        category: ["all", "custom", "new"],
        caption_preset: capPreset,
        style_preset: "smoke2_style",
        tag: `${capPreset} · ${tagVal}`
      };

      STYLE_CARDS_CATALOG.unshift(newCard);
      if (creatorDrawer) creatorDrawer.style.display = "none";
      applyStyleCardSelection(newCard, true);
    });
  }

  // Category Filters & Search in Style Hub
  let currentStyleCat = "all";
  document.querySelectorAll(".style-cat-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".style-cat-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      currentStyleCat = pill.getAttribute("data-cat");
      const q = document.getElementById("style-search-input")?.value || "";
      renderVisualStyleCards(currentStyleCat, q);
    });
  });

  const styleSearchInput = document.getElementById("style-search-input");
  if (styleSearchInput) {
    styleSearchInput.addEventListener("input", (e) => {
      renderVisualStyleCards(currentStyleCat, e.target.value);
    });
  }

  // "Create my video ->" button in Style Hub Composer -> Opens NLE Studio
  const btnHubLaunchEditor = document.getElementById("btn-hub-launch-editor");
  if (btnHubLaunchEditor) {
    btnHubLaunchEditor.addEventListener("click", () => {
      const promptVal = document.getElementById("hub-prompt-input")?.value.trim();
      switchScreenView("nle");
      if (promptVal) {
        document.getElementById("agent-cmd-input").value = promptVal;
        submitAgentCommand(promptVal);
      }
    });
  }

  const btnHubSample = document.getElementById("btn-hub-sample-clip");
  if (btnHubSample) {
    btnHubSample.addEventListener("click", () => {
      const hubStatus = document.getElementById("hub-upload-status");
      if (hubStatus) {
        hubStatus.textContent = "✓ Loaded: talking_head_mvp.mp4 (Now click any Style Card below!)";
      }
    });
  }

  // Right Inspector Tabs (Inspector | Captions (11) | Storyboard | SFX)
  document.querySelectorAll(".tool-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tool-tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.querySelectorAll(".tool-pane").forEach((p) => {
        p.style.display = p.id === targetId ? "block" : "none";
      });
    });
  });

  // Caption preset chips (11 presets)
  document.querySelectorAll(".cap-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".cap-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      const preset = chip.getAttribute("data-preset");
      state.caption_preset = preset;
      const titleWrap = document.getElementById("light-sweep-title-wrap");
      if (titleWrap) {
        titleWrap.style.display = preset === "light_sweep_title" ? "block" : "none";
      }
      const ccClip = document.getElementById("timeline-cc-clip");
      if (ccClip) {
        ccClip.textContent = `Preset: ${preset} (Word-Level Timestamps · ≥54px)`;
      }
      syncEdlInspector();
    });
  });

  const titleInput = document.getElementById("title-text-input");
  if (titleInput) {
    titleInput.addEventListener("input", (e) => {
      state.title_text = e.target.value;
      syncEdlInspector();
    });
  }

  // Export editor-job.json
  document.getElementById("btn-export-job-json").addEventListener("click", () => {
    const payload = buildExportJobPayload();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "editor-job.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Plain-language agent command bar
  async function submitAgentCommand(cmdText) {
    if (!cmdText.trim()) return;
    appendAgentChatBubble("You", cmdText, true);

    try {
      const res = await fetch(`${API_BASE}/api/agent/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmdText })
      });
      if (res.ok) {
        const data = await res.json();
        state.edl = data.edl || state.edl;
        appendAgentChatBubble("Edionic AI", data.decision.brain_trace);
        const patch = data.decision.edl_patch || {};
        if (patch.caption_preset) {
          state.caption_preset = patch.caption_preset;
          document.querySelectorAll(".cap-chip").forEach((c) => {
            c.classList.toggle("active", c.getAttribute("data-preset") === state.caption_preset);
          });
          const ccClip = document.getElementById("timeline-cc-clip");
          if (ccClip) {
            ccClip.textContent = `Preset: ${state.caption_preset} (Word-Level Timestamps · ≥54px)`;
          }
        }
        if (patch.style_preset) {
          state.style_preset = patch.style_preset;
          const inspCode = document.getElementById("inspector-style-code");
          if (inspCode) inspCode.textContent = state.style_preset;
        }
        if (patch.sfx) {
          state.sfx = patch.sfx;
          renderSfxList();
        }
        if (data.extra_results?.broll_hunt) {
          const v2Lane = document.getElementById("timeline-v2-lane");
          if (v2Lane) {
            v2Lane.innerHTML = `<span class="track-clip">Motion-Verified 9:16 B-Roll Bound (${data.extra_results.broll_hunt.placed_count || 2} clips)</span>`;
          }
        }
        syncEdlInspector();

        // Automatically trigger real FFmpeg 9:16 render when Brain Router requests it or user asks to edit/apply/cut/add!
        const triggers = data.decision.pipeline_triggers || [];
        if (triggers.includes("trigger_render")) {
          triggerRenderJob();
        }
      }
    } catch (e) {
      appendAgentChatBubble(
        "Edionic AI",
        `⚠️ Backend server was not reachable (${e.message}). Make sure start_edionic.bat or server.py is running on port 8080.`
      );
    }
  }

  document.getElementById("btn-run-cmd").addEventListener("click", () => {
    const inp = document.getElementById("agent-cmd-input");
    submitAgentCommand(inp.value);
    inp.value = "";
  });

  document.getElementById("agent-cmd-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      submitAgentCommand(e.target.value);
      e.target.value = "";
    }
  });

  document.querySelectorAll(".cmd-quick").forEach((qBtn) => {
    qBtn.addEventListener("click", () => {
      const cmd = qBtn.getAttribute("data-cmd");
      submitAgentCommand(cmd);
    });
  });

  // File upload handlers
  document.getElementById("file-upload-input").addEventListener("change", (e) => {
    handleClipUpload(e.target.files[0]);
  });
  const hubUploadInput = document.getElementById("hub-file-upload");
  if (hubUploadInput) {
    hubUploadInput.addEventListener("change", (e) => {
      handleClipUpload(e.target.files[0]);
    });
  }

  // Transport & Render buttons
  document.getElementById("btn-hello-render").addEventListener("click", triggerRenderJob);
  const btnMonitorRender = document.getElementById("btn-monitor-render");
  if (btnMonitorRender) btnMonitorRender.addEventListener("click", triggerRenderJob);

  document.getElementById("btn-play-toggle").addEventListener("click", () => {
    const v = document.getElementById("preview-video");
    if (v.paused) v.play();
    else v.pause();
  });
  document.getElementById("btn-restart").addEventListener("click", () => {
    const v = document.getElementById("preview-video");
    v.currentTime = 0;
  });

  const previewVideo = document.getElementById("preview-video");
  if (previewVideo) {
    previewVideo.addEventListener("timeupdate", () => {
      const tcEl = document.getElementById("monitor-timecode");
      const srcTc = document.getElementById("source-timecode");
      const t = previewVideo.currentTime || 0;
      const secs = Math.floor(t);
      const frames = Math.floor((t - secs) * 30);
      const str = `00:00:${String(secs).padStart(2, "0")}:${String(frames).padStart(2, "0")}`;
      if (tcEl) tcEl.textContent = str;
      if (srcTc) srcTc.textContent = str;
    });
  }
});
