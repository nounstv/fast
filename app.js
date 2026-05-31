// FAST TV & Radio Player Application Logic

// Default Cataloged Channels
const DEFAULT_CHANNELS = [
  {
    id: "abc-news",
    name: "ABC News Live",
    url: "https://abcnews-streams.akamaized.net/hls/live/2023566/abcnewshudson7/master_4000.m3u8",
    logo: "https://upload.wikimedia.org/wikipedia/commons/3/30/ABC_News_3_line_logo.svg",
    category: "Notícias",
    description: "Cobertura global e nacional de notícias 24 horas por dia, direto dos Estados Unidos pela ABC News Network.",
    logoText: "ABC"
  },
  {
    id: "rit-live",
    name: "RIT Live",
    url: "https://acesso.ecast.site:3648/live/ritlive.m3u8",
    logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Logo_RIT.png/320px-Logo_RIT.png",
    category: "Religioso",
    description: "Programação variada voltada para toda a família, unindo entretenimento de qualidade, informação e valores.",
    logoText: "RIT"
  },
  {
    id: "play-tv",
    name: "Play TV (Mono)",
    url: "https://isaocorp.cloudecast.com/playtv/tracks-v1a1/mono.m3u8",
    logo: "https://upload.wikimedia.org/wikipedia/commons/d/da/Play_TV_logo.png",
    category: "Entretenimento",
    description: "A melhor programação de videoclipes, animes, jogos, cinema e cultura pop em um só lugar.",
    logoText: "PTV"
  }
];

// =============================================
// TV PLAYER CLASS (Original)
// =============================================
class FastPlayer {
  constructor() {
    this.channels = [];
    this.currentChannel = null;
    this.hlsInstance = null;
    this.filterCategory = "all";
    this.searchQuery = "";

    // DOM Elements
    this.video = document.getElementById("video-player");
    this.loader = document.getElementById("player-loader");
    this.errorOverlay = document.getElementById("player-error");
    this.channelsListContainer = document.getElementById("channels-list");
    this.searchInput = document.getElementById("search-input");
    this.categoriesContainer = document.getElementById("categories-filter");
    
    // Custom Control Elements
    this.btnPlayPause = document.getElementById("btn-play-pause");
    this.btnMute = document.getElementById("btn-mute");
    this.volumeSlider = document.getElementById("volume-slider");
    this.btnFullscreen = document.getElementById("btn-fullscreen");
    this.btnRetry = document.getElementById("btn-retry-stream");
    
    // Display elements
    this.overlayTitle = document.getElementById("overlay-channel-title");
    this.overlayCategory = document.getElementById("overlay-channel-category");
    this.metaTitle = document.getElementById("meta-channel-title");
    this.metaCategory = document.getElementById("meta-tag-category");
    this.metaDescription = document.getElementById("meta-channel-description");

    // Modals
    this.modal = document.getElementById("add-channel-modal");
    this.btnAddCustom = document.getElementById("btn-add-custom");
    this.btnModalClose = document.getElementById("modal-close-btn");
    this.btnModalCancel = document.getElementById("modal-cancel-btn");
    this.addChannelForm = document.getElementById("add-channel-form");

    this.init();
  }

  init() {
    this.loadChannels();
    this.setupEventListeners();
    
    // Select first channel on startup
    if (this.channels.length > 0) {
      this.playChannel(this.channels[0]);
    }
    
    // Initialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  loadChannels() {
    const local = localStorage.getItem("fastplay_custom_channels");
    const custom = local ? JSON.parse(local) : [];
    this.channels = [...DEFAULT_CHANNELS, ...custom];
    this.renderChannels();
  }

  saveCustomChannel(newChannel) {
    const local = localStorage.getItem("fastplay_custom_channels");
    const custom = local ? JSON.parse(local) : [];
    custom.push(newChannel);
    localStorage.setItem("fastplay_custom_channels", JSON.stringify(custom));
    
    this.channels.push(newChannel);
    this.renderChannels();
  }

  setupEventListeners() {
    // Search & Filter
    this.searchInput.addEventListener("input", (e) => {
      this.searchQuery = e.target.value.toLowerCase();
      this.renderChannels();
    });

    this.categoriesContainer.addEventListener("click", (e) => {
      if (e.target.classList.contains("category-btn")) {
        document.querySelectorAll("#categories-filter .category-btn").forEach(btn => btn.classList.remove("active"));
        e.target.classList.add("active");
        this.filterCategory = e.target.dataset.category;
        this.renderChannels();
      }
    });

    // Custom Player Controls
    this.btnPlayPause.addEventListener("click", () => this.togglePlay());
    this.btnMute.addEventListener("click", () => this.toggleMute());
    this.volumeSlider.addEventListener("input", (e) => this.setVolume(e.target.value));
    this.btnFullscreen.addEventListener("click", () => this.toggleFullscreen());
    this.btnRetry.addEventListener("click", () => this.playChannel(this.currentChannel));

    // HTML5 Video Native Events
    this.video.addEventListener("play", () => this.updatePlayButtonState(true));
    this.video.addEventListener("pause", () => this.updatePlayButtonState(false));
    this.video.addEventListener("waiting", () => this.showLoader(true));
    this.video.addEventListener("playing", () => {
      this.showLoader(false);
      this.showError(false);
    });
    
    // Modal Event Listeners
    this.btnAddCustom.addEventListener("click", () => this.toggleModal(true));
    this.btnModalClose.addEventListener("click", () => this.toggleModal(false));
    this.btnModalCancel.addEventListener("click", () => this.toggleModal(false));
    
    this.addChannelForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const name = document.getElementById("channel-name").value;
      const url = document.getElementById("channel-url").value;
      const logo = document.getElementById("channel-logo").value || "";
      const category = document.getElementById("channel-category").value;
      const description = document.getElementById("channel-description").value || "Canal personalizado adicionado pelo usuário.";
      
      const logoText = name.substring(0, 3).toUpperCase();
      const id = "custom-" + Date.now();

      this.saveCustomChannel({ id, name, url, logo, category, description, logoText, isCustom: true });
      this.toggleModal(false);
      this.addChannelForm.reset();
      
      // Auto-play newly added channel
      const added = this.channels.find(c => c.id === id);
      if (added) this.playChannel(added);
    });

    // Close modal on background click
    window.addEventListener("click", (e) => {
      if (e.target === this.modal) {
        this.toggleModal(false);
      }
    });
  }

  toggleModal(show) {
    if (show) {
      this.modal.classList.add("show");
    } else {
      this.modal.classList.remove("show");
    }
  }

  renderChannels() {
    this.channelsListContainer.innerHTML = "";
    
    const filtered = this.channels.filter(ch => {
      const matchesSearch = ch.name.toLowerCase().includes(this.searchQuery) || 
                            ch.category.toLowerCase().includes(this.searchQuery) ||
                            ch.description.toLowerCase().includes(this.searchQuery);
      
      if (this.filterCategory === "all") {
        return matchesSearch;
      } else if (this.filterCategory === "custom") {
        return matchesSearch && ch.isCustom;
      } else {
        return matchesSearch && ch.category === this.filterCategory;
      }
    });

    if (filtered.length === 0) {
      this.channelsListContainer.innerHTML = `
        <div class="empty-state">
          <i data-lucide="tv-2" class="empty-state-icon"></i>
          <p>Nenhum canal encontrado</p>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    filtered.forEach(ch => {
      const isActive = this.currentChannel && this.currentChannel.id === ch.id;
      
      const itemHtml = document.createElement("div");
      itemHtml.className = `channel-item ${isActive ? 'active' : ''}`;
      
      const logoContent = ch.logo 
        ? `<img src="${ch.logo}" class="channel-logo-img" alt="${ch.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
           <span style="display:none; align-items:center; justify-content:center; width:100%; height:100%; font-weight:700;">${ch.logoText || ch.name.substring(0, 3).toUpperCase()}</span>`
        : (ch.logoText || ch.name.substring(0, 3).toUpperCase());

      itemHtml.innerHTML = `
        <div class="channel-logo-wrapper">
          ${logoContent}
        </div>
        <div class="channel-text-details">
          <div class="channel-item-name">${ch.name}</div>
          <div class="channel-item-category">${ch.category}</div>
        </div>
        <div class="visualizer">
          <div class="visualizer-bar"></div>
          <div class="visualizer-bar"></div>
          <div class="visualizer-bar"></div>
        </div>
      `;

      itemHtml.addEventListener("click", () => this.playChannel(ch));
      this.channelsListContainer.appendChild(itemHtml);
    });

    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  async playChannel(channel) {
    if (!channel) return;
    
    this.currentChannel = channel;
    
    // Update Active items visual state
    document.querySelectorAll(".channel-item").forEach(item => {
      item.classList.remove("active");
    });
    this.renderChannels();

    // Update Text details UI
    this.overlayTitle.textContent = channel.name;
    this.overlayCategory.textContent = channel.category;
    this.metaTitle.textContent = channel.name;
    this.metaCategory.textContent = channel.category;
    this.metaDescription.textContent = channel.description;

    // Update Logo in Player Overlay
    const playerLogoImg = document.getElementById("player-channel-logo-img");
    const playerLogoText = document.getElementById("player-channel-logo-text");
    if (channel.logo) {
      playerLogoImg.src = channel.logo;
      playerLogoImg.style.display = "block";
      playerLogoText.style.display = "none";
      playerLogoImg.onerror = () => {
        playerLogoImg.style.display = "none";
        playerLogoText.style.display = "block";
        playerLogoText.textContent = channel.logoText || channel.name.substring(0, 3).toUpperCase();
      };
    } else {
      playerLogoImg.style.display = "none";
      playerLogoText.style.display = "block";
      playerLogoText.textContent = channel.logoText || channel.name.substring(0, 3).toUpperCase();
    }

    // Update Logo in Meta Card
    const metaLogoImg = document.getElementById("meta-channel-logo-img");
    const metaLogoText = document.getElementById("meta-channel-logo-text");
    if (channel.logo) {
      metaLogoImg.src = channel.logo;
      metaLogoImg.style.display = "block";
      metaLogoText.style.display = "none";
      metaLogoImg.onerror = () => {
        metaLogoImg.style.display = "none";
        metaLogoText.style.display = "block";
        metaLogoText.textContent = channel.logoText || channel.name.substring(0, 3).toUpperCase();
      };
    } else {
      metaLogoImg.style.display = "none";
      metaLogoText.style.display = "block";
      metaLogoText.textContent = channel.logoText || channel.name.substring(0, 3).toUpperCase();
    }

    this.showLoader(true);
    this.showError(false);

    // Stop current stream before loading new one
    if (this.hlsInstance) {
      this.hlsInstance.destroy();
      this.hlsInstance = null;
    }

    const streamUrl = channel.url;

    if (Hls.isSupported()) {
      const hls = new Hls({
        maxMaxBufferLength: 10,
        enableWorker: true,
        lowLatencyMode: true
      });
      this.hlsInstance = hls;
      hls.loadSource(streamUrl);
      hls.attachMedia(this.video);
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        this.video.play().catch(err => {
          console.log("Auto-play blocked, waiting for interaction", err);
          this.updatePlayButtonState(false);
          this.showLoader(false);
        });
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error("HLS Error:", data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.log("Fatal network error, trying to recover...");
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.log("Fatal media error, trying to recover...");
              hls.recoverMediaError();
              break;
            default:
              this.handlePlaybackError();
              break;
          }
        }
      });
    } 
    // Native HLS (iOS Safari)
    else if (this.video.canPlayType('application/vnd.apple.mpegurl')) {
      this.video.src = streamUrl;
      this.video.addEventListener('canplay', () => {
        this.video.play().catch(err => {
          console.log("Auto-play blocked natively", err);
          this.updatePlayButtonState(false);
          this.showLoader(false);
        });
      });

      this.video.addEventListener('error', () => {
        this.handlePlaybackError();
      });
    } 
    else {
      this.handlePlaybackError("Seu navegador não suporta reprodução HLS (.m3u8).");
    }
  }

  stopPlayback() {
    if (this.hlsInstance) {
      this.hlsInstance.destroy();
      this.hlsInstance = null;
    }
    this.video.pause();
    this.video.removeAttribute('src');
    this.video.load();
  }

  togglePlay() {
    if (this.video.paused) {
      this.video.play().catch(e => console.log(e));
    } else {
      this.video.pause();
    }
  }

  updatePlayButtonState(isPlaying) {
    const icon = this.btnPlayPause.querySelector("i") || document.getElementById("icon-play-pause");
    if (isPlaying) {
      icon.setAttribute("data-lucide", "pause");
    } else {
      icon.setAttribute("data-lucide", "play");
    }
    if (window.lucide) window.lucide.createIcons();
  }

  toggleMute() {
    this.video.muted = !this.video.muted;
    this.updateMuteButtonState();
  }

  setVolume(value) {
    this.video.volume = value;
    this.video.muted = value == 0;
    this.updateMuteButtonState();
  }

  updateMuteButtonState() {
    const icon = this.btnMute.querySelector("i") || document.getElementById("icon-mute");
    this.volumeSlider.value = this.video.muted ? 0 : this.video.volume;

    if (this.video.muted || this.video.volume === 0) {
      icon.setAttribute("data-lucide", "volume-x");
    } else if (this.video.volume < 0.5) {
      icon.setAttribute("data-lucide", "volume-1");
    } else {
      icon.setAttribute("data-lucide", "volume-2");
    }
    if (window.lucide) window.lucide.createIcons();
  }

  toggleFullscreen() {
    const playerWrapper = document.getElementById("player-wrapper");
    if (!document.fullscreenElement) {
      playerWrapper.requestFullscreen().catch(err => {
        console.error(`Error enabling fullscreen: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  }

  showLoader(show) {
    this.loader.style.display = show ? "flex" : "none";
  }

  showError(show, message = "") {
    this.errorOverlay.style.display = show ? "flex" : "none";
    if (show && message) {
      document.getElementById("error-desc").textContent = message;
    }
  }

  handlePlaybackError(customMessage = null) {
    this.showLoader(false);
    this.showError(true, customMessage);
  }
}


// =============================================
// RADIO PLAYER CLASS
// =============================================
class RadioPlayer {
  constructor() {
    this.stations = [];
    this.currentStation = null;
    this.isPlaying = false;
    this.filterCategory = "all";
    this.filterCountry = "all";
    this.searchQuery = "";
    this.isLoading = false;
    this.allCountries = [];

    // Radio-Browser API servers (round-robin)
    this.apiServers = [
      "https://de1.api.radio-browser.info",
      "https://nl1.api.radio-browser.info",
      "https://at1.api.radio-browser.info"
    ];
    this.currentApiIndex = 0;

    // DOM Elements
    this.audio = document.getElementById("radio-audio-player");
    this.playerWrapper = document.getElementById("radio-player-wrapper");
    this.loader = document.getElementById("radio-loader");
    this.errorOverlay = document.getElementById("radio-error");
    this.stationsListContainer = document.getElementById("radio-stations-list");
    this.stationsLoading = document.getElementById("radio-stations-loading");
    this.searchInput = document.getElementById("radio-search-input");
    this.categoriesContainer = document.getElementById("radio-categories-filter");

    // Control elements
    this.btnPlayPause = document.getElementById("radio-btn-play-pause");
    this.btnStop = document.getElementById("radio-btn-stop");
    this.btnMute = document.getElementById("radio-btn-mute");
    this.volumeSlider = document.getElementById("radio-volume-slider");
    this.btnRetry = document.getElementById("radio-btn-retry");

    // Display elements
    this.stationName = document.getElementById("radio-station-name");
    this.stationTagline = document.getElementById("radio-station-tagline");
    this.stationArtText = document.getElementById("radio-art-text");
    this.stationArtImg = document.getElementById("radio-art-img");
    this.metaTitle = document.getElementById("radio-meta-title");
    this.metaTag = document.getElementById("radio-meta-tag");
    this.metaCodec = document.getElementById("radio-meta-codec");
    this.metaBitrate = document.getElementById("radio-meta-bitrate");
    this.metaDescription = document.getElementById("radio-meta-description");

    this.setupEventListeners();
  }

  get apiBase() {
    return this.apiServers[this.currentApiIndex];
  }

  rotateServer() {
    this.currentApiIndex = (this.currentApiIndex + 1) % this.apiServers.length;
  }

  setupEventListeners() {
    // Search
    this.searchInput.addEventListener("input", (e) => {
      this.searchQuery = e.target.value.toLowerCase();
      this.renderStations();
    });

    // Category filter
    this.categoriesContainer.addEventListener("click", (e) => {
      if (e.target.classList.contains("radio-cat-btn")) {
        document.querySelectorAll(".radio-cat-btn").forEach(btn => btn.classList.remove("active"));
        e.target.classList.add("active");
        this.filterCategory = e.target.dataset.category;
        this.renderStations();
      }
    });

    // Controls
    this.btnPlayPause.addEventListener("click", () => this.togglePlay());
    this.btnStop.addEventListener("click", () => this.stopPlayback());
    this.btnMute.addEventListener("click", () => this.toggleMute());
    this.volumeSlider.addEventListener("input", (e) => this.setVolume(e.target.value));
    this.btnRetry.addEventListener("click", () => {
      if (this.currentStation) this.playStation(this.currentStation);
    });

    // Audio events
    this.audio.addEventListener("playing", () => {
      this.isPlaying = true;
      this.showLoader(false);
      this.showError(false);
      this.updatePlayState();
    });

    this.audio.addEventListener("pause", () => {
      this.isPlaying = false;
      this.updatePlayState();
    });

    this.audio.addEventListener("waiting", () => {
      this.showLoader(true);
    });

    this.audio.addEventListener("error", (e) => {
      console.error("Radio audio error:", e);
      this.handleError("Não foi possível sintonizar esta estação. A transmissão pode estar indisponível.");
    });
  }

  async fetchStations() {
    this.stationsLoading.style.display = "flex";
    this.stationsListContainer.style.display = "none";

    // 1. Try loading from Famelack radio JSON (baixar_tudo.py)
    try {
      const response = await fetch("downloads/radio_famelack/radio_todos.json");
      if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
          this.stations = this.normalizeStations(data);
          this.allCountries = this.extractCountries(this.stations);
          console.log(`Loaded ${this.stations.length} radio stations from Famelack (${this.allCountries.length} countries)`);
          this.buildCountryFilter();
          this.stationsLoading.style.display = "none";
          this.stationsListContainer.style.display = "flex";
          this.renderStations();
          return;
        }
      }
    } catch (e) { /* continue */ }

    // 2. Try loading from Radio-Browser global JSON (baixar_radios.py)
    try {
      const response = await fetch("downloads/radios_GLOBAL.json");
      if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
          this.stations = this.normalizeStations(data);
          this.allCountries = this.extractCountries(this.stations);
          console.log(`Loaded ${this.stations.length} radio stations from GLOBAL JSON (${this.allCountries.length} countries)`);
          this.buildCountryFilter();
          this.stationsLoading.style.display = "none";
          this.stationsListContainer.style.display = "flex";
          this.renderStations();
          return;
        }
      }
    } catch (e) { /* continue */ }

    // 2. Try loading from per-country index
    try {
      const indexResp = await fetch("downloads/radios/index.json");
      if (indexResp.ok) {
        const index = await indexResp.json();
        if (Array.isArray(index) && index.length > 0) {
          console.log(`Found country index with ${index.length} countries, loading...`);
          
          let allStations = [];
          let loaded = 0;
          
          for (const entry of index) {
            try {
              const countryResp = await fetch(`downloads/radios/${entry.code}.json`);
              if (countryResp.ok) {
                const countryData = await countryResp.json();
                if (Array.isArray(countryData)) {
                  allStations = allStations.concat(countryData);
                  loaded++;
                }
              }
            } catch (e) { /* skip this country */ }
          }
          
          if (allStations.length > 0) {
            this.stations = this.normalizeStations(allStations);
            this.allCountries = this.extractCountries(this.stations);
            console.log(`Loaded ${this.stations.length} stations from ${loaded} country files`);
            this.buildCountryFilter();
            this.stationsLoading.style.display = "none";
            this.stationsListContainer.style.display = "flex";
            this.renderStations();
            return;
          }
        }
      }
    } catch (e) { /* continue */ }

    // 3. Try single-country local files
    const localFiles = [
      "downloads/radios_BRA.json",
      "downloads/radios_BR.json"
    ];

    for (const file of localFiles) {
      try {
        const response = await fetch(file);
        if (!response.ok) continue;
        
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
          this.stations = this.normalizeStations(data);
          console.log(`Loaded ${this.stations.length} radio stations from local file: ${file}`);
          this.stationsLoading.style.display = "none";
          this.stationsListContainer.style.display = "flex";
          this.renderStations();
          return;
        }
      } catch (e) { /* continue */ }
    }

    // 4. Fallback: fetch from Radio-Browser API
    console.log("No local radio JSON found, fetching from API...");
    
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const url = `${this.apiBase}/json/stations/bycountry/Brazil?limit=500&order=votes&reverse=true&hidebroken=true`;
        
        const response = await fetch(url, {
          headers: { "User-Agent": "FastPlay/1.0" }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        this.stations = data
          .filter(s => s.url_resolved && s.name)
          .map(s => ({
            id: s.stationuuid,
            name: s.name.trim(),
            url: s.url_resolved,
            favicon: s.favicon || "",
            tags: (s.tags || "").toLowerCase(),
            codec: s.codec || "MP3",
            bitrate: s.bitrate || 0,
            votes: s.votes || 0,
            country: s.countrycode || "BR",
            countryName: s.country || "",
            state: s.state || "",
            language: s.language || "portuguese",
            homepage: s.homepage || "",
            category: this.categorizeStation(s)
          }));

        console.log(`Loaded ${this.stations.length} radio stations from ${this.apiBase}`);
        
        this.stationsLoading.style.display = "none";
        this.stationsListContainer.style.display = "flex";
        this.renderStations();
        return;

      } catch (err) {
        console.warn(`Failed to fetch from ${this.apiBase}:`, err.message);
        this.rotateServer();
      }
    }

    // All sources failed
    this.stationsLoading.innerHTML = `
      <i data-lucide="wifi-off" style="width: 36px; height: 36px; color: var(--danger-color);"></i>
      <p>Falha ao carregar estações</p>
      <p style="font-size: 12px; color: var(--text-dark); margin-top: 4px;">Execute <code>python3 baixar_radios.py</code> para baixar offline</p>
      <button class="btn radio-btn-accent" onclick="window.radioPlayer.fetchStations()">
        <i data-lucide="refresh-cw"></i>
        Tentar Novamente
      </button>
    `;
    if (window.lucide) window.lucide.createIcons();
  }

  normalizeStations(data) {
    return data.map(s => ({
      id: s.id || "",
      name: (s.name || "").trim(),
      url: s.url || "",
      favicon: s.favicon || "",
      tags: (s.tags || "").toLowerCase(),
      codec: s.codec || "MP3",
      bitrate: s.bitrate || 0,
      votes: s.votes || 0,
      country: (s.country || s.countryCode || "??").toUpperCase(),
      countryName: s.countryName || "",
      state: s.state || "",
      language: s.language || "",
      homepage: s.homepage || "",
      category: s.category || this.categorizeStation(s)
    }));
  }

  extractCountries(stations) {
    const countryMap = {};
    stations.forEach(s => {
      const code = s.country || "??";
      if (!countryMap[code]) {
        countryMap[code] = { code, name: s.countryName || code, count: 0 };
      }
      countryMap[code].count++;
    });
    return Object.values(countryMap).sort((a, b) => b.count - a.count);
  }

  buildCountryFilter() {
    if (!this.allCountries || this.allCountries.length <= 1) return;
    
    // Create country selector dropdown
    let countrySelect = document.getElementById("radio-country-select");
    if (!countrySelect) {
      const wrapper = document.createElement("div");
      wrapper.className = "radio-country-filter";
      wrapper.innerHTML = `
        <select id="radio-country-select" class="form-input radio-country-select-input">
          <option value="all">🌍 Todos os países (${this.stations.length})</option>
        </select>
      `;
      
      // Insert before the genre filter
      this.categoriesContainer.parentNode.insertBefore(wrapper, this.categoriesContainer);
      countrySelect = document.getElementById("radio-country-select");
      
      countrySelect.addEventListener("change", (e) => {
        this.filterCountry = e.target.value;
        this.renderStations();
      });
    }

    // Populate options
    countrySelect.innerHTML = `<option value="all">🌍 Todos os países (${this.stations.length})</option>`;
    
    // Country flag emoji helper
    const flagEmoji = (code) => {
      if (!code || code.length !== 2) return "🏳️";
      return String.fromCodePoint(...[...code.toUpperCase()].map(c => 0x1F1E6 + c.charCodeAt(0) - 65));
    };

    this.allCountries.forEach(c => {
      const flag = flagEmoji(c.code);
      const label = c.name || c.code;
      const opt = document.createElement("option");
      opt.value = c.code;
      opt.textContent = `${flag} ${label} (${c.count})`;
      countrySelect.appendChild(opt);
    });
  }

  categorizeStation(station) {
    const tags = (station.tags || "").toLowerCase();
    const name = (station.name || "").toLowerCase();
    const combined = tags + " " + name;

    if (combined.includes("sertanejo") || combined.includes("country")) return "sertanejo";
    if (combined.includes("gospel") || combined.includes("religios") || combined.includes("evangel") || combined.includes("católic") || combined.includes("catolic")) return "gospel";
    if (combined.includes("rock") || combined.includes("metal") || combined.includes("punk") || combined.includes("indie")) return "rock";
    if (combined.includes("pop") || combined.includes("hits") || combined.includes("top 40")) return "pop";
    if (combined.includes("mpb") || combined.includes("bossa") || combined.includes("brasileir")) return "mpb";
    if (combined.includes("pagode") || combined.includes("samba") || combined.includes("axé") || combined.includes("axe")) return "pagode";
    if (combined.includes("news") || combined.includes("notícia") || combined.includes("noticia") || combined.includes("jornalism") || combined.includes("cbn") || combined.includes("band news") || combined.includes("jovem pan news")) return "news";
    if (combined.includes("eletronic") || combined.includes("edm") || combined.includes("dance") || combined.includes("techno") || combined.includes("house")) return "pop";
    if (combined.includes("jazz") || combined.includes("blues") || combined.includes("soul") || combined.includes("r&b")) return "mpb";
    if (combined.includes("clássic") || combined.includes("classic") || combined.includes("erudita")) return "mpb";
    if (combined.includes("forró") || combined.includes("forro") || combined.includes("forrozao")) return "sertanejo";
    if (combined.includes("funk") || combined.includes("hip hop") || combined.includes("rap")) return "pop";
    
    return "pop"; // default
  }

  renderStations() {
    this.stationsListContainer.innerHTML = "";
    
    const filtered = this.stations.filter(st => {
      const matchesSearch = st.name.toLowerCase().includes(this.searchQuery) ||
                            st.tags.includes(this.searchQuery) ||
                            st.state.toLowerCase().includes(this.searchQuery) ||
                            st.category.includes(this.searchQuery) ||
                            (st.countryName || "").toLowerCase().includes(this.searchQuery) ||
                            (st.country || "").toLowerCase().includes(this.searchQuery);

      // Country filter
      if (this.filterCountry && this.filterCountry !== "all") {
        if (st.country !== this.filterCountry) return false;
      }

      if (this.filterCategory === "all") {
        return matchesSearch;
      }
      return matchesSearch && st.category === this.filterCategory;
    });

    if (filtered.length === 0) {
      this.stationsListContainer.innerHTML = `
        <div class="empty-state">
          <i data-lucide="radio" class="empty-state-icon"></i>
          <p>Nenhuma estação encontrada</p>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    filtered.forEach(st => {
      const isActive = this.currentStation && this.currentStation.id === st.id;

      const itemEl = document.createElement("div");
      itemEl.className = `channel-item radio-station-item ${isActive ? "active" : ""}`;
      
      const logoContent = st.favicon 
        ? `<img src="${st.favicon}" class="channel-logo-img" alt="${st.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
           <span style="display:none; align-items:center; justify-content:center; width:100%; height:100%; font-weight:700;">${st.name.substring(0, 2).toUpperCase()}</span>`
        : st.name.substring(0, 2).toUpperCase();

      const bitrateText = st.bitrate > 0 ? `${st.bitrate} kbps` : "";

      itemEl.innerHTML = `
        <div class="channel-logo-wrapper">
          ${logoContent}
        </div>
        <div class="channel-text-details">
          <div class="channel-item-name">${st.name}</div>
          <div class="channel-item-category">${this.getCategoryLabel(st.category)}${st.state ? ` · ${st.state}` : ""}</div>
          ${bitrateText ? `<div class="channel-item-bitrate">${st.codec} · ${bitrateText}</div>` : ""}
        </div>
        <div class="visualizer">
          <div class="visualizer-bar"></div>
          <div class="visualizer-bar"></div>
          <div class="visualizer-bar"></div>
        </div>
      `;

      itemEl.addEventListener("click", () => this.playStation(st));
      this.stationsListContainer.appendChild(itemEl);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  getCategoryLabel(cat) {
    const labels = {
      pop: "Pop / Hits",
      rock: "Rock",
      sertanejo: "Sertanejo",
      gospel: "Gospel",
      mpb: "MPB / Jazz",
      pagode: "Pagode / Samba",
      news: "Notícias"
    };
    return labels[cat] || cat;
  }

  async playStation(station) {
    if (!station) return;
    
    this.currentStation = station;
    this.showLoader(true);
    this.showError(false);

    // Stop current audio
    this.audio.pause();
    this.audio.removeAttribute("src");

    // Update UI
    this.stationName.textContent = station.name;
    this.stationTagline.textContent = `${this.getCategoryLabel(station.category)}${station.state ? ` · ${station.state}` : ""}`;
    
    // Update art
    if (station.favicon) {
      this.stationArtImg.src = station.favicon;
      this.stationArtImg.style.display = "block";
      this.stationArtText.style.display = "none";
      
      this.stationArtImg.onerror = () => {
        this.stationArtImg.style.display = "none";
        this.stationArtText.style.display = "block";
        this.stationArtText.textContent = station.name.substring(0, 2).toUpperCase();
      };
    } else {
      this.stationArtImg.style.display = "none";
      this.stationArtText.style.display = "block";
      this.stationArtText.textContent = station.name.substring(0, 2).toUpperCase();
    }

    // Update meta card
    this.metaTitle.textContent = station.name;
    this.metaTag.textContent = this.getCategoryLabel(station.category);
    this.metaCodec.textContent = station.codec || "Audio Stream";
    this.metaBitrate.textContent = station.bitrate > 0 ? `${station.bitrate} kbps` : "";
    
    let descParts = [];
    if (station.state) descParts.push(`📍 ${station.state}, Brasil`);
    if (station.tags) {
      const tagList = station.tags.split(",").slice(0, 5).map(t => t.trim()).filter(Boolean).join(", ");
      if (tagList) descParts.push(`🏷️ ${tagList}`);
    }
    if (station.homepage) descParts.push(`🌐 ${station.homepage}`);
    this.metaDescription.textContent = descParts.join("  ·  ") || "Estação de rádio ao vivo do Brasil.";

    // Re-render list to update active state
    this.renderStations();

    // Play the stream
    try {
      // Check if it's an HLS stream
      if (station.url.includes(".m3u8") && Hls.isSupported()) {
        // Use HLS.js for m3u8 streams
        if (this._hlsInstance) {
          this._hlsInstance.destroy();
        }
        const hls = new Hls({ enableWorker: true });
        this._hlsInstance = hls;
        hls.loadSource(station.url);
        hls.attachMedia(this.audio);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          this.audio.play().catch(e => {
            console.log("Radio auto-play blocked:", e);
            this.showLoader(false);
          });
        });
        hls.on(Hls.Events.ERROR, (_, data) => {
          if (data.fatal) {
            this.handleError("Erro ao sintonizar esta estação HLS.");
          }
        });
      } else {
        // Direct audio stream
        this.audio.src = station.url;
        this.audio.load();
        await this.audio.play();
      }
    } catch (err) {
      console.error("Error playing radio:", err);
      this.handleError("Não foi possível iniciar a reprodução desta estação.");
    }

    // Register a "click" on Radio-Browser to help their stats
    this.registerClick(station.id);
  }

  async registerClick(stationId) {
    try {
      await fetch(`${this.apiBase}/json/url/${stationId}`, { method: "GET" });
    } catch (e) {
      // Silent fail, this is just analytics
    }
  }

  togglePlay() {
    if (!this.currentStation) return;
    
    if (this.isPlaying) {
      this.audio.pause();
    } else {
      if (!this.audio.src && this.currentStation) {
        this.playStation(this.currentStation);
      } else {
        this.audio.play().catch(e => console.log(e));
      }
    }
  }

  stopPlayback() {
    if (this._hlsInstance) {
      this._hlsInstance.destroy();
      this._hlsInstance = null;
    }
    this.audio.pause();
    this.audio.removeAttribute("src");
    this.audio.load();
    this.isPlaying = false;
    this.updatePlayState();
  }

  toggleMute() {
    this.audio.muted = !this.audio.muted;
    this.updateMuteState();
  }

  setVolume(value) {
    this.audio.volume = value;
    this.audio.muted = value == 0;
    this.updateMuteState();
  }

  updatePlayState() {
    const icon = document.getElementById("radio-icon-play");
    if (this.isPlaying) {
      icon.setAttribute("data-lucide", "pause");
      this.playerWrapper.classList.add("radio-playing");
    } else {
      icon.setAttribute("data-lucide", "play");
      this.playerWrapper.classList.remove("radio-playing");
    }
    if (window.lucide) window.lucide.createIcons();
  }

  updateMuteState() {
    const icon = document.getElementById("radio-icon-mute");
    this.volumeSlider.value = this.audio.muted ? 0 : this.audio.volume;

    if (this.audio.muted || this.audio.volume === 0) {
      icon.setAttribute("data-lucide", "volume-x");
    } else if (this.audio.volume < 0.5) {
      icon.setAttribute("data-lucide", "volume-1");
    } else {
      icon.setAttribute("data-lucide", "volume-2");
    }
    if (window.lucide) window.lucide.createIcons();
  }

  showLoader(show) {
    this.loader.style.display = show ? "flex" : "none";
  }

  showError(show, message = "") {
    this.errorOverlay.style.display = show ? "flex" : "none";
    if (show && message) {
      document.getElementById("radio-error-desc").textContent = message;
    }
  }

  handleError(message) {
    this.isPlaying = false;
    this.updatePlayState();
    this.showLoader(false);
    this.showError(true, message);
  }
}


// =============================================
// MODE SWITCHER CONTROLLER
// =============================================
class AppController {
  constructor() {
    this.currentMode = "tv";
    this.tvContainer = document.getElementById("tv-container");
    this.radioContainer = document.getElementById("radio-container");
    this.logoTag = document.getElementById("logo-tag-label");
    this.modeTvBtn = document.getElementById("mode-tv-btn");
    this.modeRadioBtn = document.getElementById("mode-radio-btn");

    this.tvPlayer = null;
    this.radioPlayer = null;

    this.setupModeSwitcher();
  }

  setupModeSwitcher() {
    this.modeTvBtn.addEventListener("click", () => this.switchMode("tv"));
    this.modeRadioBtn.addEventListener("click", () => this.switchMode("radio"));
  }

  switchMode(mode) {
    if (mode === this.currentMode) return;
    this.currentMode = mode;

    // Update buttons
    this.modeTvBtn.classList.toggle("active", mode === "tv");
    this.modeRadioBtn.classList.toggle("active", mode === "radio");

    // Update containers
    if (mode === "tv") {
      this.tvContainer.style.display = "grid";
      this.radioContainer.style.display = "none";
      document.body.classList.remove("radio-active");
      this.logoTag.textContent = "FAST TV";
      
      // Pause radio when switching to TV
      if (this.radioPlayer) {
        this.radioPlayer.stopPlayback();
      }
    } else {
      this.tvContainer.style.display = "none";
      this.radioContainer.style.display = "grid";
      document.body.classList.add("radio-active");
      this.logoTag.textContent = "RÁDIO";

      // Pause TV when switching to Radio
      if (this.tvPlayer) {
        this.tvPlayer.stopPlayback();
      }
      
      // Fetch radio stations on first visit
      if (this.radioPlayer && this.radioPlayer.stations.length === 0) {
        this.radioPlayer.fetchStations();
      }
    }

    // Re-initialize icons
    if (window.lucide) window.lucide.createIcons();
  }
}


// =============================================
// INITIALIZATION
// =============================================
document.addEventListener("DOMContentLoaded", () => {
  const app = new AppController();
  
  // Initialize TV Player
  app.tvPlayer = new FastPlayer();
  window.fastPlayer = app.tvPlayer;
  
  // Initialize Radio Player
  app.radioPlayer = new RadioPlayer();
  window.radioPlayer = app.radioPlayer;
  
  window.appController = app;
});
