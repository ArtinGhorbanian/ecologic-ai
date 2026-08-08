"use strict";

(() => {
    const API = Object.freeze({
        session: "/api/v1/session",
        health: "/api/v1/health",
        analyses: "/api/v1/analyses",
        coach: "/api/v1/coach",
        chat: "/api/v1/chat",
        history: "/api/v1/history",
        historyItem: (id) => `/api/v1/history/${encodeURIComponent(String(id))}`
    });

    const ALLOWED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
    const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
    const MAX_IMAGE_PIXELS = 24_000_000;
    const SVG_NS = "http://www.w3.org/2000/svg";
    const DEFAULT_DISCLAIMER = "This is an automated decision-support estimate, not a site inspection, certification, diagnosis, or guarantee.";

    class ApiError extends Error {
        constructor(message, status = 0, code = "request_failed", requestId = "") {
            super(message);
            this.name = "ApiError";
            this.status = status;
            this.code = code;
            this.requestId = requestId;
        }
    }

    const state = {
        csrfToken: "",
        sessionPromise: null,
        sessionReady: false,
        healthReady: false,
        provider: null,
        providerMode: "unknown",
        selectedImage: null,
        lastAnalysisPayload: null,
        analysis: null,
        analysisId: null,
        historyItems: new Map(),
        deleteTarget: null,
        recognition: null,
        isListening: false,
        isAnalysisPending: false,
        isCoachPending: false,
        isChatPending: false,
        chatHistory: [],
        chatContextId: null,
        roadmapCompleted: 0,
        dialogReturnFocus: new Map()
    };

    let elements = {};

    function initialize() {
        cacheElements();
        bindEvents();
        updateCharacterCount();
        setModeBadge("checking", "Mode: checking");
        setServiceStatus("checking", "Checking service status");
        void initializeService();
    }

    function cacheElements() {
        elements = {
            csrfMeta: document.querySelector('meta[name="csrf-token"]'),
            modeBadge: document.getElementById("modeBadge"),
            serviceStatus: document.getElementById("serviceStatus"),
            analysisForm: document.getElementById("analysisForm"),
            userInput: document.getElementById("userInput"),
            inputCount: document.getElementById("inputCount"),
            observationError: document.getElementById("observationError"),
            imageInput: document.getElementById("imageInput"),
            imageStatus: document.getElementById("imageStatus"),
            demoImageDisclosure: document.getElementById("demoImageDisclosure"),
            imagePreview: document.getElementById("imagePreview"),
            previewImage: document.getElementById("previewImage"),
            previewName: document.getElementById("previewName"),
            previewMeta: document.getElementById("previewMeta"),
            removeImageButton: document.getElementById("removeImageButton"),
            micButton: document.getElementById("micButton"),
            micButtonLabel: document.getElementById("micButtonLabel"),
            analyzeButton: document.getElementById("analyzeButton"),
            analyzeButtonLabel: document.getElementById("analyzeButtonLabel"),
            analysisStatus: document.getElementById("analysisStatus"),
            analysisError: document.getElementById("analysisError"),
            analysisErrorMessage: document.getElementById("analysisErrorMessage"),
            retryAnalysisButton: document.getElementById("retryAnalysisButton"),
            dismissAnalysisError: document.getElementById("dismissAnalysisError"),
            historyToggle: document.getElementById("historyToggle"),
            historyPanel: document.getElementById("historyPanel"),
            historyStatus: document.getElementById("historyStatus"),
            historyList: document.getElementById("historyList"),
            emptyState: document.getElementById("emptyState"),
            resultContainer: document.getElementById("resultContainer"),
            resultTitle: document.getElementById("resultTitle"),
            resultSummary: document.getElementById("resultSummary"),
            statusBadge: document.getElementById("statusBadge"),
            isoBadge: document.getElementById("isoBadge"),
            assessmentDisclaimer: document.querySelector(".assessment-disclaimer"),
            categoryValue: document.getElementById("categoryValue"),
            riskCard: document.getElementById("riskCard"),
            riskValue: document.getElementById("riskValue"),
            riskLabel: document.getElementById("riskLabel"),
            potentialValue: document.getElementById("potentialValue"),
            evidenceValue: document.getElementById("evidenceValue"),
            riskBreakdownSection: document.getElementById("riskBreakdownSection"),
            riskBreakdownList: document.getElementById("riskBreakdownList"),
            assessmentMessage: document.getElementById("assessmentMessage"),
            causesRegion: document.getElementById("causesRegion"),
            causesList: document.getElementById("causesList"),
            scoreContextToggle: document.getElementById("scoreContextToggle"),
            scoreContextContent: document.getElementById("scoreContextContent"),
            scoreContextGrid: document.getElementById("scoreContextGrid"),
            scoreContextMarker: document.getElementById("scoreContextMarker"),
            scoreContextDot: document.getElementById("scoreContextDot"),
            scoreContextValueLabel: document.getElementById("scoreContextValueLabel"),
            scoreContextChartDescription: document.getElementById("scoreContextChartDescription"),
            scoreContextTableBody: document.getElementById("scoreContextTableBody"),
            roadmapList: document.getElementById("roadmapList"),
            roadmapEmpty: document.getElementById("roadmapEmpty"),
            roadmapProgress: document.getElementById("roadmapProgress"),
            roadmapProgressLabel: document.getElementById("roadmapProgressLabel"),
            coachButton: document.getElementById("coachButton"),
            coachStatus: document.getElementById("coachStatus"),
            coachResult: document.getElementById("coachResult"),
            coachMessage: document.getElementById("coachMessage"),
            coachTipRow: document.getElementById("coachTipRow"),
            coachTip: document.getElementById("coachTip"),
            coachNoteRow: document.getElementById("coachNoteRow"),
            coachNote: document.getElementById("coachNote"),
            openChatButton: document.getElementById("openChatButton"),
            chatFab: document.getElementById("chatFab"),
            chatDialog: document.getElementById("chatDialog"),
            chatHistory: document.getElementById("chatHistory"),
            chatStatus: document.getElementById("chatStatus"),
            chatForm: document.getElementById("chatForm"),
            chatInput: document.getElementById("chatInput"),
            sendChatButton: document.getElementById("sendChatButton"),
            deleteDialog: document.getElementById("deleteDialog"),
            deleteForm: document.getElementById("deleteForm"),
            deleteItemLabel: document.getElementById("deleteItemLabel"),
            deleteStatus: document.getElementById("deleteStatus"),
            cancelDeleteButton: document.getElementById("cancelDeleteButton"),
            confirmDeleteButton: document.getElementById("confirmDeleteButton"),
            celebrationDialog: document.getElementById("celebrationDialog"),
            globalAnnouncer: document.getElementById("globalAnnouncer")
        };

        const metaToken = elements.csrfMeta?.content?.trim();
        if (metaToken) {
            state.csrfToken = metaToken;
        }
    }

    function bindEvents() {
        elements.analysisForm.addEventListener("submit", handleAnalysisSubmit);
        elements.userInput.addEventListener("input", () => {
            updateCharacterCount();
            clearObservationError();
        });

        document.querySelectorAll("[data-example]").forEach((button) => {
            button.addEventListener("click", () => {
                elements.userInput.value = button.dataset.example || "";
                updateCharacterCount();
                clearObservationError();
                elements.userInput.focus();
            });
        });

        elements.imageInput.addEventListener("change", handleImageSelection);
        elements.removeImageButton.addEventListener("click", removeSelectedImage);
        elements.micButton.addEventListener("click", toggleVoiceInput);
        elements.retryAnalysisButton.addEventListener("click", retryLastAnalysis);
        elements.dismissAnalysisError.addEventListener("click", hideAnalysisError);
        elements.historyToggle.addEventListener("click", toggleHistoryPanel);
        elements.historyList.addEventListener("click", handleHistoryAction);
        elements.scoreContextToggle.addEventListener("click", toggleScoreContext);
        elements.roadmapList.addEventListener("change", handleRoadmapChange);
        elements.coachButton.addEventListener("click", requestCoachExplanation);
        elements.openChatButton.addEventListener("click", openChatDialog);
        elements.chatFab.addEventListener("click", openChatDialog);
        elements.chatForm.addEventListener("submit", handleChatSubmit);
        elements.chatInput.addEventListener("keydown", handleChatKeydown);
        elements.deleteForm.addEventListener("submit", confirmHistoryDeletion);
        elements.cancelDeleteButton.addEventListener("click", () => elements.deleteDialog.close("cancel"));

        [elements.chatDialog, elements.deleteDialog, elements.celebrationDialog].forEach((dialog) => {
            dialog.addEventListener("close", () => restoreDialogFocus(dialog));
        });
    }

    async function initializeService() {
        const [sessionResult, healthResult] = await Promise.allSettled([
            ensureSession(true),
            loadHealth()
        ]);

        if (sessionResult.status === "rejected" && healthResult.status === "rejected") {
            setModeBadge("unknown", "Mode not reported");
            setServiceStatus("unavailable", "Service status unavailable");
            return;
        }

        updateServiceSummary();
    }

    async function ensureSession(force = false) {
        if (!force && state.sessionReady && state.csrfToken) {
            return;
        }

        if (state.sessionPromise) {
            return state.sessionPromise;
        }

        state.sessionPromise = (async () => {
            try {
                const data = await requestJson(API.session, { timeout: 10_000, includeCsrf: false });
                const token = textValue(data.csrf_token);
                if (!token) {
                    throw new ApiError("The service did not provide a session token.", 0, "missing_csrf_token");
                }
                state.csrfToken = token;
                state.sessionReady = true;
                state.provider = data.provider ?? null;
                applyProviderIndicator(state.provider);
            } catch (error) {
                state.sessionReady = false;
                throw error;
            } finally {
                state.sessionPromise = null;
            }
        })();

        return state.sessionPromise;
    }

    async function loadHealth() {
        try {
            const data = await requestJson(API.health, { timeout: 8_000, includeCsrf: false });
            const status = textValue(data.status || data.health).toLowerCase();
            state.healthReady = data.healthy === true || data.ok === true || ["ok", "healthy", "ready"].includes(status);
            if (!state.healthReady && status) {
                setServiceStatus("limited", `Service reports: ${status}`);
            }
        } catch (error) {
            state.healthReady = false;
            throw error;
        }
    }

    function updateServiceSummary() {
        if (state.healthReady) {
            setServiceStatus("ready", "Service responding");
        } else if (state.sessionReady) {
            setServiceStatus("limited", "Session ready; health not reported");
        } else {
            setServiceStatus("unavailable", "Service status unavailable");
        }

        if (!state.provider) {
            setModeBadge("unknown", "Mode not reported");
        }
    }

    function applyProviderIndicator(provider) {
        const providerObject = provider && typeof provider === "object" ? provider : {};
        const mode = providerModeFrom(provider);

        if (mode === "live") {
            setModeBadge("live", providerObject.live_calls_enabled === true ? "Live calls enabled" : "Live provider");
            return;
        }

        if (mode === "demo") {
            setModeBadge("demo", "Demo mode");
            return;
        }

        setModeBadge("unknown", "Mode not reported");
    }

    function providerModeFrom(provider) {
        const providerObject = provider && typeof provider === "object" ? provider : {};
        const providerText = typeof provider === "string"
            ? provider
            : textValue(providerObject.mode || providerObject.environment || providerObject.status || providerObject.kind);
        const normalized = providerText.toLowerCase();

        if (providerObject.live === true || providerObject.live_calls_enabled === true || ["live", "live_api", "openai", "production"].includes(normalized)) {
            return "live";
        }

        if (providerObject.demo === true || ["demo", "demo_mode", "local", "fallback", "fallback_mode", "mock"].includes(normalized)) {
            return "demo";
        }

        return "unknown";
    }

    function setModeBadge(mode, label) {
        state.providerMode = mode;
        elements.modeBadge.dataset.mode = mode;
        elements.modeBadge.textContent = label;
        elements.demoImageDisclosure.hidden = mode !== "demo";
        updateSelectedImageStatus();
    }

    function setServiceStatus(status, label) {
        elements.serviceStatus.dataset.state = status;
        const dot = elements.serviceStatus.querySelector(".service-status__dot");
        elements.serviceStatus.replaceChildren();
        if (dot) {
            elements.serviceStatus.append(dot);
        } else {
            const replacementDot = createElement("span", "service-status__dot");
            replacementDot.setAttribute("aria-hidden", "true");
            elements.serviceStatus.append(replacementDot);
        }
        elements.serviceStatus.append(document.createTextNode(label));
    }

    async function handleAnalysisSubmit(event) {
        event.preventDefault();
        if (state.isAnalysisPending) {
            return;
        }

        const payload = buildAnalysisPayload();
        if (!payload) {
            return;
        }

        state.lastAnalysisPayload = payload;
        await submitAnalysis(payload);
    }

    function buildAnalysisPayload() {
        const text = elements.userInput.value.trim();
        if (!text) {
            showObservationError("Describe the environmental observation before requesting an assessment.");
            elements.userInput.focus();
            return null;
        }

        const payload = {
            text,
            locale: inferLocale(text)
        };

        if (state.selectedImage) {
            payload.image = { data_url: state.selectedImage.dataUrl };
        }

        return payload;
    }

    async function submitAnalysis(payload) {
        setAnalysisPending(true);
        hideAnalysisError();
        elements.analysisStatus.textContent = "Reviewing the observation and available evidence…";

        try {
            await ensureSession();
            const response = await requestJson(API.analyses, {
                method: "POST",
                body: payload,
                timeout: 75_000
            });

            const analysis = normalizeAnalysis(response.analysis);
            if (!analysis.id) {
                throw new ApiError("The assessment response did not include an analysis ID.", 0, "invalid_analysis_response");
            }

            state.analysis = analysis;
            state.analysisId = analysis.id;
            state.chatHistory = [];
            state.chatContextId = null;
            renderAnalysis(analysis, getEvidenceLabel(payload, analysis));
            applyProviderIndicator(analysis.provider);
            elements.analysisStatus.textContent = "Assessment ready. Review its assumptions before acting.";
            announce("Assessment ready.");
            focusResults();

            if (!elements.historyPanel.hidden) {
                void loadHistory();
            }
        } catch (error) {
            showAnalysisError(friendlyErrorMessage(error, "The service could not complete the assessment."));
            elements.analysisStatus.textContent = "Assessment not completed.";
        } finally {
            setAnalysisPending(false);
        }
    }

    async function retryLastAnalysis() {
        if (!state.lastAnalysisPayload || state.isAnalysisPending) {
            return;
        }
        await submitAnalysis(state.lastAnalysisPayload);
    }

    function setAnalysisPending(pending) {
        state.isAnalysisPending = pending;
        elements.analyzeButton.disabled = pending;
        elements.analysisForm.setAttribute("aria-busy", String(pending));
        elements.analyzeButtonLabel.textContent = pending ? "Assessing observation…" : "Assess observation";
    }

    function showObservationError(message) {
        elements.observationError.textContent = message;
        elements.observationError.hidden = false;
        elements.userInput.setAttribute("aria-invalid", "true");
    }

    function clearObservationError() {
        elements.observationError.textContent = "";
        elements.observationError.hidden = true;
        elements.userInput.removeAttribute("aria-invalid");
    }

    function showAnalysisError(message) {
        elements.analysisErrorMessage.textContent = message;
        elements.analysisError.hidden = false;
        announce(message);
    }

    function hideAnalysisError() {
        elements.analysisErrorMessage.textContent = "";
        elements.analysisError.hidden = true;
    }

    function normalizeAnalysis(rawAnalysis) {
        const raw = rawAnalysis && typeof rawAnalysis === "object" ? rawAnalysis : {};
        const riskNumber = numberOrNull(raw.risk);
        const roadmap = Array.isArray(raw.roadmap)
            ? raw.roadmap.map((step, index) => normalizeRoadmapStep(step, index)).filter(Boolean)
            : [];
        const causes = Array.isArray(raw.causes)
            ? raw.causes.map((cause) => textValue(cause)).filter(Boolean)
            : [];

        return {
            id: raw.id ?? null,
            createdAt: textValue(raw.created_at),
            kind: textValue(raw.kind),
            locale: textValue(raw.locale, "en"),
            provider: raw.provider ?? null,
            category: textValue(raw.category, "Not reported"),
            analysisMode: textValue(raw.analysis_mode),
            risk: riskNumber === null ? null : clamp(riskNumber, 0, 100),
            riskBreakdown: normalizeBreakdown(raw.risk_breakdown),
            causes,
            status: textValue(raw.status, "Assessment ready"),
            message: textValue(raw.message, "No decision summary was returned."),
            roadmap,
            financialPotential: textValue(raw.financial_potential, "Not estimated"),
            isoReference: textValue(raw.iso_reference),
            kpiLabel: textValue(raw.kpi_label),
            confidenceNote: textValue(raw.confidence_note),
            disclaimer: textValue(raw.disclaimer, DEFAULT_DISCLAIMER)
        };
    }

    function normalizeRoadmapStep(step, index) {
        if (!step || typeof step !== "object") {
            return null;
        }
        const task = textValue(step.task || step.title);
        if (!task) {
            return null;
        }
        return {
            phase: textValue(step.phase, `Step ${index + 1}`),
            task,
            detail: textValue(step.detail || step.description)
        };
    }

    function normalizeBreakdown(value) {
        if (!value || typeof value !== "object" || Array.isArray(value)) {
            return [];
        }

        return Object.entries(value)
            .map(([key, rawValue]) => {
                const numericValue = numberOrNull(rawValue);
                if (numericValue === null) {
                    return null;
                }
                return {
                    key,
                    label: breakdownLabel(key),
                    value: clamp(numericValue, 0, 100)
                };
            })
            .filter(Boolean);
    }

    function renderAnalysis(analysis, evidenceLabel) {
        elements.emptyState.hidden = true;
        elements.resultContainer.hidden = false;
        elements.chatFab.hidden = false;
        elements.resultContainer.lang = analysis.locale || "en";

        elements.categoryValue.textContent = analysis.category;
        elements.statusBadge.textContent = analysis.status;
        elements.assessmentMessage.textContent = analysis.message;
        elements.potentialValue.textContent = analysis.financialPotential;
        elements.evidenceValue.textContent = evidenceLabel;
        elements.resultSummary.textContent = analysis.confidenceNote || "Review the evidence, assumptions, and recommended actions together.";
        elements.assessmentDisclaimer.textContent = analysis.disclaimer || DEFAULT_DISCLAIMER;

        renderRisk(analysis.risk);
        renderIsoReference(analysis.isoReference);
        renderRiskBreakdown(analysis.riskBreakdown);
        renderCauses(analysis.causes);
        renderScoreContext(analysis.risk);
        renderRoadmap(analysis.roadmap);
        resetCoach();
        resetChatForAnalysis(analysis.id);
    }

    function renderRisk(risk) {
        if (risk === null) {
            elements.riskValue.textContent = "Not reported";
            elements.riskLabel.textContent = "No numeric score returned";
            elements.riskCard.dataset.level = "neutral";
            elements.scoreContextToggle.disabled = true;
            elements.scoreContextContent.hidden = true;
            elements.scoreContextToggle.setAttribute("aria-expanded", "false");
            setScoreContextToggleLabel("Score context unavailable");
            return;
        }

        const roundedRisk = Math.round(risk);
        elements.riskValue.textContent = `${roundedRisk}/100`;
        elements.riskLabel.textContent = "Provider-supplied current score";
        elements.riskCard.dataset.level = "neutral";
        elements.scoreContextToggle.disabled = false;
        setScoreContextToggleLabel(elements.scoreContextContent.hidden ? "Show score context" : "Hide score context");
    }

    function renderIsoReference(reference) {
        if (!reference || reference.toUpperCase() === "N/A") {
            elements.isoBadge.textContent = "";
            elements.isoBadge.hidden = true;
            return;
        }
        elements.isoBadge.textContent = `Reference only: ${reference}`;
        elements.isoBadge.hidden = false;
    }

    function renderRiskBreakdown(items) {
        elements.riskBreakdownList.replaceChildren();
        if (!items.length) {
            elements.riskBreakdownSection.hidden = true;
            return;
        }

        items.forEach((item, index) => {
            const listItem = createElement("li", "risk-breakdown-item");
            const progressId = `risk-dimension-${index}`;
            const label = createElement("label", "", item.label);
            label.htmlFor = progressId;
            const output = createElement("output", "", `${Math.round(item.value)}/100`);
            output.setAttribute("for", progressId);
            const progress = createElement("progress");
            progress.id = progressId;
            progress.max = 100;
            progress.value = item.value;
            progress.textContent = `${Math.round(item.value)} out of 100 points`;
            listItem.append(label, output, progress);
            elements.riskBreakdownList.append(listItem);
        });

        elements.riskBreakdownSection.hidden = false;
    }

    function renderCauses(causes) {
        elements.causesList.replaceChildren();
        if (!causes.length) {
            elements.causesRegion.hidden = true;
            return;
        }

        causes.forEach((cause) => {
            elements.causesList.append(createElement("li", "", cause));
        });
        elements.causesRegion.hidden = false;
    }

    function renderScoreContext(risk) {
        elements.scoreContextGrid.replaceChildren();
        elements.scoreContextTableBody.replaceChildren();
        [elements.scoreContextMarker, elements.scoreContextDot, elements.scoreContextValueLabel].forEach((element) => {
            element.setAttribute("hidden", "");
        });

        if (risk === null) {
            elements.scoreContextChartDescription.textContent = "No numeric score was returned. No score context, forecast, target, or severity threshold is available.";
            return;
        }

        const width = 720;
        const left = 54;
        const right = 18;
        const scaleY = 96;
        const plotWidth = width - left - right;
        const roundedRisk = Math.round(risk);
        const x = (value) => left + (value / 100) * plotWidth;

        const scaleLine = createSvgElement("line", "score-scale-line");
        scaleLine.setAttribute("x1", String(left));
        scaleLine.setAttribute("x2", String(width - right));
        scaleLine.setAttribute("y1", String(scaleY));
        scaleLine.setAttribute("y2", String(scaleY));
        elements.scoreContextGrid.append(scaleLine);

        [0, 25, 50, 75, 100].forEach((value) => {
            const tick = createSvgElement("line", "score-scale-tick");
            tick.setAttribute("x1", String(x(value)));
            tick.setAttribute("x2", String(x(value)));
            tick.setAttribute("y1", String(scaleY - 8));
            tick.setAttribute("y2", String(scaleY + 8));

            const label = createSvgElement("text", "score-axis-label");
            label.setAttribute("x", String(x(value)));
            label.setAttribute("y", String(scaleY + 32));
            label.setAttribute("text-anchor", value === 0 ? "start" : value === 100 ? "end" : "middle");
            label.textContent = String(value);
            elements.scoreContextGrid.append(tick, label);
        });

        const scoreX = x(roundedRisk);
        elements.scoreContextMarker.setAttribute("x1", String(scoreX));
        elements.scoreContextMarker.setAttribute("x2", String(scoreX));
        elements.scoreContextMarker.setAttribute("y1", "48");
        elements.scoreContextMarker.setAttribute("y2", String(scaleY));
        elements.scoreContextDot.setAttribute("cx", String(scoreX));
        elements.scoreContextDot.setAttribute("cy", String(scaleY));
        elements.scoreContextValueLabel.setAttribute("x", String(scoreX));
        elements.scoreContextValueLabel.setAttribute("y", "37");
        elements.scoreContextValueLabel.setAttribute("text-anchor", roundedRisk <= 5 ? "start" : roundedRisk >= 95 ? "end" : "middle");
        elements.scoreContextValueLabel.textContent = `${roundedRisk}/100`;
        [elements.scoreContextMarker, elements.scoreContextDot, elements.scoreContextValueLabel].forEach((element) => {
            element.removeAttribute("hidden");
        });

        elements.scoreContextChartDescription.textContent = `The current automated score is ${roundedRisk} out of 100. No forecast, target, trend, probability, or severity threshold was generated.`;
        const row = document.createElement("tr");
        row.append(
            createElement("th", "", "Current automated score"),
            createElement("td", "", `${roundedRisk}/100`)
        );
        row.firstElementChild.scope = "row";
        elements.scoreContextTableBody.append(row);
    }

    function renderRoadmap(roadmap) {
        elements.roadmapList.replaceChildren();
        elements.roadmapEmpty.hidden = roadmap.length > 0;
        elements.roadmapProgress.max = Math.max(roadmap.length, 1);
        elements.roadmapProgress.value = 0;
        state.roadmapCompleted = 0;
        updateRoadmapProgress(roadmap.length);

        roadmap.forEach((step, index) => {
            const item = createElement("li", "roadmap-item");
            item.dataset.complete = "false";
            const article = document.createElement("article");
            const header = createElement("div", "roadmap-item__header");
            const phase = createElement("span", "roadmap-phase", step.phase);
            const titleId = `roadmap-title-${index}`;
            const checkboxLabel = createElement("label", "roadmap-check");
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.dataset.roadmapIndex = String(index);
            checkbox.setAttribute("aria-labelledby", titleId);
            checkboxLabel.append(checkbox);
            header.append(phase, checkboxLabel);

            const title = createElement("h4", "", step.task);
            title.id = titleId;
            article.append(header, title);

            if (step.detail) {
                const details = createElement("details", "roadmap-detail");
                const summary = createElement("summary", "", "View implementation detail");
                const detail = createElement("p", "", step.detail);
                details.append(summary, detail);
                article.append(details);
            }

            item.append(article);
            elements.roadmapList.append(item);
        });
    }

    function handleRoadmapChange(event) {
        const checkbox = event.target.closest('input[type="checkbox"][data-roadmap-index]');
        if (!checkbox) {
            return;
        }

        const item = checkbox.closest(".roadmap-item");
        if (item) {
            item.dataset.complete = String(checkbox.checked);
        }

        const total = elements.roadmapList.querySelectorAll('input[type="checkbox"]').length;
        const completed = elements.roadmapList.querySelectorAll('input[type="checkbox"]:checked').length;
        const previouslyCompleted = state.roadmapCompleted;
        state.roadmapCompleted = completed;
        updateRoadmapProgress(total);

        if (total > 0 && completed === total && previouslyCompleted < total) {
            openDialog(elements.celebrationDialog, checkbox);
        }
    }

    function updateRoadmapProgress(total) {
        elements.roadmapProgress.max = Math.max(total, 1);
        elements.roadmapProgress.value = state.roadmapCompleted;
        elements.roadmapProgressLabel.textContent = `${state.roadmapCompleted} of ${total} marked complete`;
    }

    function toggleScoreContext() {
        if (elements.scoreContextToggle.disabled) {
            return;
        }
        const willOpen = elements.scoreContextContent.hidden;
        elements.scoreContextContent.hidden = !willOpen;
        elements.scoreContextToggle.setAttribute("aria-expanded", String(willOpen));
        setScoreContextToggleLabel(willOpen ? "Hide score context" : "Show score context");
    }

    function setScoreContextToggleLabel(label) {
        const textNode = Array.from(elements.scoreContextToggle.childNodes).find((node) => node.nodeType === Node.TEXT_NODE);
        if (textNode) {
            textNode.textContent = `${label} `;
        } else {
            elements.scoreContextToggle.prepend(document.createTextNode(`${label} `));
        }
    }

    async function requestCoachExplanation() {
        if (!state.analysisId || state.isCoachPending) {
            return;
        }

        setCoachPending(true);
        elements.coachStatus.textContent = "Preparing a plain-language explanation…";
        try {
            await ensureSession();
            const data = await requestJson(API.coach, {
                method: "POST",
                body: { analysis_id: state.analysisId },
                timeout: 35_000
            });
            const coach = data.coach && typeof data.coach === "object" ? data.coach : data;
            const message = textValue(coach.human_message || coach.message || coach.explanation);
            const tip = textValue(coach.eco_tip || coach.tip);
            const note = textValue(coach.confidence_note || coach.context_note);

            if (!message) {
                throw new ApiError("The coach response did not include an explanation.", 0, "invalid_coach_response");
            }

            elements.coachMessage.textContent = message;
            elements.coachTip.textContent = tip;
            elements.coachNote.textContent = note;
            elements.coachTipRow.hidden = !tip;
            elements.coachNoteRow.hidden = !note;
            elements.coachResult.hidden = false;
            elements.coachStatus.textContent = "Explanation ready. It does not change the assessment.";
        } catch (error) {
            elements.coachStatus.textContent = friendlyErrorMessage(error, "Eco-Coach could not prepare an explanation.");
        } finally {
            setCoachPending(false);
        }
    }

    function setCoachPending(pending) {
        state.isCoachPending = pending;
        elements.coachButton.disabled = pending;
        elements.coachButton.textContent = pending ? "Preparing explanation…" : "Explain this assessment";
    }

    function resetCoach() {
        elements.coachStatus.textContent = "";
        elements.coachResult.hidden = true;
        elements.coachMessage.textContent = "";
        elements.coachTip.textContent = "";
        elements.coachNote.textContent = "";
        elements.coachTipRow.hidden = false;
        elements.coachNoteRow.hidden = false;
        setCoachPending(false);
    }

    async function toggleHistoryPanel() {
        const willOpen = elements.historyPanel.hidden;
        elements.historyPanel.hidden = !willOpen;
        elements.historyToggle.setAttribute("aria-expanded", String(willOpen));
        if (willOpen) {
            await loadHistory();
        }
    }

    async function loadHistory() {
        elements.historyStatus.textContent = "Loading saved assessments…";
        elements.historyList.replaceChildren();
        try {
            const data = await requestJson(API.history, { timeout: 15_000, includeCsrf: false });
            const items = Array.isArray(data.items) ? data.items : [];
            renderHistory(items);
            elements.historyStatus.textContent = items.length
                ? `${items.length} saved assessment${items.length === 1 ? "" : "s"}.`
                : "No saved assessments yet.";
        } catch (error) {
            elements.historyStatus.textContent = friendlyErrorMessage(error, "Saved assessments could not be loaded.");
        }
    }

    function renderHistory(items) {
        state.historyItems.clear();
        elements.historyList.replaceChildren();

        items.forEach((item) => {
            if (!item || item.id === undefined || item.id === null) {
                return;
            }

            const key = String(item.id);
            state.historyItems.set(key, item);
            const listItem = createElement("li", "history-item");
            const selectButton = createElement("button", "history-card");
            selectButton.type = "button";
            selectButton.dataset.historyId = key;

            const titleRow = createElement("span", "history-card__title");
            titleRow.append(
                createElement("strong", "", textValue(item.category, "Saved assessment")),
                createElement("span", "history-risk", formatRisk(item.risk_score))
            );
            const metaRow = createElement("span", "history-card__meta");
            metaRow.append(
                createElement("span", "", formatDate(item.created_at)),
                createElement("span", "", textValue(item.input_excerpt, "View result"))
            );
            selectButton.append(titleRow, metaRow);

            const deleteButton = createElement("button", "history-delete");
            deleteButton.type = "button";
            deleteButton.dataset.deleteId = key;
            deleteButton.setAttribute("aria-label", `Delete saved assessment: ${textValue(item.category, "assessment")}`);
            deleteButton.append(createIcon("#icon-trash"));

            listItem.append(selectButton, deleteButton);
            elements.historyList.append(listItem);
        });
    }

    function handleHistoryAction(event) {
        const deleteButton = event.target.closest("[data-delete-id]");
        if (deleteButton) {
            openDeleteDialog(deleteButton.dataset.deleteId, deleteButton);
            return;
        }

        const selectButton = event.target.closest("[data-history-id]");
        if (!selectButton) {
            return;
        }

        const item = state.historyItems.get(selectButton.dataset.historyId);
        if (!item || !item.result) {
            elements.historyStatus.textContent = "This saved entry does not contain a readable result.";
            return;
        }

        const analysis = normalizeAnalysis(item.result);
        if (!analysis.id) {
            analysis.id = item.id;
        }
        state.analysis = analysis;
        state.analysisId = analysis.id;
        state.chatHistory = [];
        state.chatContextId = null;
        renderAnalysis(analysis, evidenceLabelFromKind(analysis.kind, true, analysis.provider));
        applyProviderIndicator(analysis.provider);
        focusResults();

        if (window.matchMedia("(max-width: 1023px)").matches) {
            elements.historyPanel.hidden = true;
            elements.historyToggle.setAttribute("aria-expanded", "false");
        }
    }

    function openDeleteDialog(id, trigger) {
        const item = state.historyItems.get(String(id));
        if (!item) {
            return;
        }
        state.deleteTarget = String(id);
        elements.deleteItemLabel.textContent = `${textValue(item.category, "Assessment")} · ${formatDate(item.created_at)}`;
        elements.deleteStatus.textContent = "";
        openDialog(elements.deleteDialog, trigger);
    }

    async function confirmHistoryDeletion(event) {
        event.preventDefault();
        if (!state.deleteTarget) {
            return;
        }

        const targetId = state.deleteTarget;
        elements.confirmDeleteButton.disabled = true;
        elements.confirmDeleteButton.textContent = "Deleting entry…";
        elements.deleteStatus.textContent = "Removing the entry from saved history…";

        try {
            await ensureSession();
            await requestJson(API.historyItem(targetId), {
                method: "DELETE",
                timeout: 20_000
            });
            state.deleteTarget = null;
            elements.deleteDialog.close("deleted");
            announce("Saved assessment removed from history.");
            await loadHistory();
        } catch (error) {
            elements.deleteStatus.textContent = friendlyErrorMessage(error, "The saved assessment could not be removed.");
        } finally {
            elements.confirmDeleteButton.disabled = false;
            elements.confirmDeleteButton.textContent = "Delete entry";
        }
    }

    function openChatDialog(event) {
        if (!state.analysisId) {
            return;
        }
        resetChatForAnalysis(state.analysisId);
        openDialog(elements.chatDialog, event?.currentTarget || document.activeElement);
        window.setTimeout(() => elements.chatInput.focus(), 0);
    }

    function resetChatForAnalysis(analysisId) {
        if (state.chatContextId === String(analysisId)) {
            return;
        }
        state.chatContextId = String(analysisId);
        state.chatHistory = [];
        elements.chatHistory.replaceChildren();
        elements.chatStatus.textContent = "";
        appendChatMessage("assistant", "Ask about assumptions, priorities, or next steps in this assessment.");
    }

    async function handleChatSubmit(event) {
        event.preventDefault();
        if (state.isChatPending || !state.analysisId) {
            return;
        }

        const message = elements.chatInput.value.trim();
        if (!message) {
            elements.chatStatus.textContent = "Enter a follow-up question before sending.";
            elements.chatInput.focus();
            return;
        }

        const previousHistory = state.chatHistory.slice(-6).map((turn) => ({
            role: turn.role,
            content: turn.content.slice(0, 600)
        }));
        appendChatMessage("user", message);
        state.chatHistory.push({ role: "user", content: message });
        elements.chatInput.value = "";
        setChatPending(true);
        elements.chatStatus.textContent = "EcoLogic is preparing a reply…";

        try {
            await ensureSession();
            const data = await requestJson(API.chat, {
                method: "POST",
                body: {
                    analysis_id: state.analysisId,
                    message,
                    history: previousHistory
                },
                timeout: 45_000
            });
            const chat = data.chat && typeof data.chat === "object" ? data.chat : data;
            const reply = textValue(chat.reply || chat.message || chat.content);
            if (!reply) {
                throw new ApiError("The chat response did not include a reply.", 0, "invalid_chat_response");
            }
            appendChatMessage("assistant", reply);
            state.chatHistory.push({ role: "assistant", content: reply });
            elements.chatStatus.textContent = "Reply ready. Verify it before acting.";
        } catch (error) {
            elements.chatStatus.textContent = friendlyErrorMessage(error, "The follow-up reply could not be completed.");
        } finally {
            setChatPending(false);
            elements.chatInput.focus();
        }
    }

    function handleChatKeydown(event) {
        if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            elements.chatForm.requestSubmit();
        }
    }

    function setChatPending(pending) {
        state.isChatPending = pending;
        elements.sendChatButton.disabled = pending;
        elements.chatInput.disabled = pending;
        elements.chatForm.setAttribute("aria-busy", String(pending));
    }

    function appendChatMessage(role, content) {
        const wrapper = createElement("article", `chat-message chat-message--${role}`);
        const label = createElement("span", "chat-message__label", role === "user" ? "You" : "EcoLogic");
        const bubble = createElement("p", "chat-message__bubble", content);
        bubble.dir = "auto";
        wrapper.append(label, bubble);
        elements.chatHistory.append(wrapper);
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }

    async function handleImageSelection(event) {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }

        elements.imageStatus.textContent = "Checking image…";
        try {
            validateImageFile(file);
            await validateImageDimensions(file);
            const dataUrl = await readFileAsDataUrl(file);
            if (!dataUrl.startsWith(`data:${file.type};base64,`)) {
                throw new Error("The selected file could not be read as a supported image.");
            }
            state.selectedImage = {
                dataUrl,
                name: file.name,
                size: file.size,
                type: file.type
            };
            elements.previewImage.src = dataUrl;
            elements.previewImage.alt = `Preview of ${file.name}`;
            elements.previewName.textContent = file.name;
            elements.previewMeta.textContent = `${humanImageType(file.type)} · ${formatBytes(file.size)}`;
            elements.imagePreview.hidden = false;
            updateSelectedImageStatus();
        } catch (error) {
            removeSelectedImage();
            elements.imageStatus.textContent = error instanceof Error ? error.message : "The selected image could not be used.";
        }
    }

    function validateImageFile(file) {
        if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
            throw new Error("Choose a JPEG, PNG, or WebP image.");
        }
        if (file.size <= 0) {
            throw new Error("The selected image is empty.");
        }
        if (file.size > MAX_IMAGE_BYTES) {
            throw new Error("The selected image is larger than 2 MB.");
        }
    }

    async function validateImageDimensions(file) {
        if (!("createImageBitmap" in window)) {
            return;
        }
        let bitmap;
        try {
            bitmap = await createImageBitmap(file);
            if (bitmap.width * bitmap.height > MAX_IMAGE_PIXELS) {
                throw new Error("The image dimensions are too large. Choose an image under 24 megapixels.");
            }
        } catch (error) {
            if (error instanceof Error && error.message.includes("24 megapixels")) {
                throw error;
            }
            throw new Error("The selected file is not a readable image.");
        } finally {
            bitmap?.close();
        }
    }

    function removeSelectedImage() {
        state.selectedImage = null;
        if (state.lastAnalysisPayload?.image) {
            state.lastAnalysisPayload = { ...state.lastAnalysisPayload };
            delete state.lastAnalysisPayload.image;
        }
        elements.imageInput.value = "";
        elements.previewImage.removeAttribute("src");
        elements.previewImage.alt = "Selected image preview";
        elements.previewName.textContent = "";
        elements.previewMeta.textContent = "";
        elements.imagePreview.hidden = true;
        if (!elements.imageStatus.textContent.includes("larger") && !elements.imageStatus.textContent.includes("Choose")) {
            elements.imageStatus.textContent = "";
        }
    }

    function updateSelectedImageStatus() {
        if (!state.selectedImage) {
            return;
        }

        if (state.providerMode === "demo") {
            elements.imageStatus.textContent = "Image attached, but demo mode will not inspect its pixels. Describe visual evidence in the observation text.";
        } else if (state.providerMode === "live") {
            elements.imageStatus.textContent = "Image ready to include with the assessment.";
        } else {
            elements.imageStatus.textContent = "Image attached. Provider image capability is not reported, so describe visual evidence in the observation text.";
        }
    }

    function toggleVoiceInput() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            elements.analysisStatus.textContent = "Voice input is not supported by this browser. You can continue by typing.";
            return;
        }

        if (!state.recognition) {
            state.recognition = new SpeechRecognition();
            state.recognition.continuous = false;
            state.recognition.interimResults = false;
            state.recognition.onstart = () => setListeningState(true);
            state.recognition.onend = () => setListeningState(false);
            state.recognition.onresult = (event) => {
                const transcript = textValue(event.results?.[0]?.[0]?.transcript);
                if (transcript) {
                    const separator = elements.userInput.value.trim() ? " " : "";
                    elements.userInput.value = `${elements.userInput.value.trimEnd()}${separator}${transcript}`.slice(0, 4000);
                    updateCharacterCount();
                    clearObservationError();
                }
            };
            state.recognition.onerror = (event) => {
                setListeningState(false);
                const errorMessages = {
                    "not-allowed": "Microphone access was not allowed. Check browser permissions or continue by typing.",
                    "no-speech": "No speech was detected. Try again or continue by typing.",
                    "audio-capture": "No microphone was available. Continue by typing."
                };
                elements.analysisStatus.textContent = errorMessages[event.error] || "Voice input stopped before text could be captured.";
            };
        }

        if (state.isListening) {
            state.recognition.stop();
        } else {
            state.recognition.lang = inferLocale(elements.userInput.value);
            try {
                state.recognition.start();
            } catch (error) {
                elements.analysisStatus.textContent = "Voice input is already starting. Please wait a moment.";
            }
        }
    }

    function setListeningState(listening) {
        state.isListening = listening;
        elements.micButton.setAttribute("aria-pressed", String(listening));
        elements.micButtonLabel.textContent = listening ? "Stop listening" : "Use voice";
        const use = elements.micButton.querySelector("use");
        if (use) {
            use.setAttribute("href", listening ? "#icon-stop" : "#icon-mic");
        }
        elements.analysisStatus.textContent = listening ? "Listening for one observation…" : "";
    }

    function updateCharacterCount() {
        elements.inputCount.textContent = `${elements.userInput.value.length.toLocaleString()} / 4,000`;
    }

    function focusResults() {
        window.requestAnimationFrame(() => {
            elements.resultTitle.focus({ preventScroll: true });
            elements.resultContainer.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
        });
    }

    function openDialog(dialog, trigger) {
        if (dialog.open) {
            return;
        }
        state.dialogReturnFocus.set(dialog, trigger || document.activeElement);
        dialog.showModal();
    }

    function restoreDialogFocus(dialog) {
        const returnTarget = state.dialogReturnFocus.get(dialog);
        state.dialogReturnFocus.delete(dialog);
        if (returnTarget instanceof HTMLElement && returnTarget.isConnected) {
            returnTarget.focus();
        }
    }

    async function requestJson(url, options = {}) {
        const {
            method = "GET",
            body,
            timeout = 30_000,
            includeCsrf = method !== "GET"
        } = options;
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), timeout);
        const headers = new Headers({ Accept: "application/json" });

        if (body !== undefined) {
            headers.set("Content-Type", "application/json");
        }
        if (includeCsrf && state.csrfToken) {
            headers.set("X-CSRF-Token", state.csrfToken);
        }

        try {
            const response = await fetch(url, {
                method,
                headers,
                body: body === undefined ? undefined : JSON.stringify(body),
                credentials: "same-origin",
                signal: controller.signal
            });
            const rawText = await response.text();
            let data = {};
            if (rawText) {
                try {
                    data = JSON.parse(rawText);
                } catch (error) {
                    throw new ApiError("The service returned an unreadable response.", response.status, "invalid_json");
                }
            }

            if (!response.ok) {
                const apiError = data.error && typeof data.error === "object" ? data.error : {};
                if (response.status === 403) {
                    state.csrfToken = "";
                    state.sessionReady = false;
                }
                throw new ApiError(
                    textValue(apiError.message, `Request failed with status ${response.status}.`),
                    response.status,
                    textValue(apiError.code, "request_failed"),
                    textValue(apiError.request_id)
                );
            }

            return data;
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            if (error instanceof DOMException && error.name === "AbortError") {
                throw new ApiError("The request timed out. Check the connection and try again.", 408, "request_timeout");
            }
            throw new ApiError("The service could not be reached. Check the connection and try again.", 0, "network_error");
        } finally {
            window.clearTimeout(timeoutId);
        }
    }

    function friendlyErrorMessage(error, fallback) {
        if (!(error instanceof Error)) {
            return fallback;
        }
        const baseMessage = error.message || fallback;
        if (error instanceof ApiError && error.requestId) {
            return `${baseMessage} Request reference: ${error.requestId}.`;
        }
        return baseMessage;
    }

    function inferLocale(text) {
        if (/[؀-ۿ]/u.test(text)) {
            const browserLocale = navigator.language || "fa-IR";
            return browserLocale.toLowerCase().startsWith("ar") ? "ar" : "fa";
        }
        return navigator.language || document.documentElement.lang || "en";
    }

    function getEvidenceLabel(payload, analysis) {
        if (payload.image?.data_url) {
            const mode = providerModeFrom(analysis.provider);
            if (mode === "demo") {
                return "Text used; image not inspected in demo";
            }
            return mode === "live" ? "Text and image" : "Text and image submitted";
        }
        return evidenceLabelFromKind(analysis.kind, false, analysis.provider);
    }

    function evidenceLabelFromKind(kind, saved, provider = null) {
        const normalized = textValue(kind).toLowerCase();
        if (normalized.includes("image") || normalized.includes("vision") || normalized.includes("multi")) {
            if (providerModeFrom(provider) === "demo") {
                return saved ? "Saved text; image not inspected in demo" : "Text used; image not inspected in demo";
            }
            return saved ? "Saved text and image" : "Text and image";
        }
        return saved ? "Saved text observation" : "Text observation";
    }

    function breakdownLabel(key) {
        const labels = {
            financial_risk: "Financial risk",
            operational_risk: "Operational risk",
            safety_risk: "Safety risk",
            environmental_risk: "Environmental risk",
            water: "Water",
            energy: "Energy",
            waste: "Waste",
            carbon: "Carbon"
        };
        if (labels[key]) {
            return labels[key];
        }
        return key
            .replace(/[_-]+/g, " ")
            .replace(/\b\w/g, (character) => character.toUpperCase());
    }

    function formatRisk(value) {
        const numericValue = numberOrNull(value);
        return numericValue === null ? "Risk score not reported" : `${Math.round(clamp(numericValue, 0, 100))}/100 risk score`;
    }

    function formatDate(value) {
        if (!value) {
            return "Date not reported";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return textValue(value, "Date not reported");
        }
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: "medium",
            timeStyle: "short"
        }).format(date);
    }

    function formatBytes(bytes) {
        if (bytes < 1024) {
            return `${bytes} B`;
        }
        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(1)} KB`;
        }
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    function humanImageType(type) {
        return {
            "image/jpeg": "JPEG",
            "image/png": "PNG",
            "image/webp": "WebP"
        }[type] || "Image";
    }

    function createElement(tagName, className = "", text = "") {
        const element = document.createElement(tagName);
        if (className) {
            element.className = className;
        }
        if (text !== "") {
            element.textContent = text;
        }
        return element;
    }

    function createSvgElement(tagName, className = "") {
        const element = document.createElementNS(SVG_NS, tagName);
        if (className) {
            element.setAttribute("class", className);
        }
        return element;
    }

    function createIcon(symbolHref) {
        const svg = createSvgElement("svg", "icon");
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("viewBox", "0 0 24 24");
        const use = createSvgElement("use");
        use.setAttribute("href", symbolHref);
        svg.append(use);
        return svg;
    }

    function textValue(value, fallback = "") {
        if (typeof value === "string") {
            return value.trim() || fallback;
        }
        if (typeof value === "number" || typeof value === "boolean") {
            return String(value);
        }
        return fallback;
    }

    function numberOrNull(value) {
        if (value === null || value === undefined || value === "") {
            return null;
        }
        const numericValue = Number(value);
        return Number.isFinite(numericValue) ? numericValue : null;
    }

    function clamp(value, minimum, maximum) {
        return Math.min(maximum, Math.max(minimum, value));
    }

    function readFileAsDataUrl(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ""));
            reader.onerror = () => reject(new Error("The selected image could not be read."));
            reader.readAsDataURL(file);
        });
    }

    function announce(message) {
        elements.globalAnnouncer.textContent = "";
        window.requestAnimationFrame(() => {
            elements.globalAnnouncer.textContent = message;
        });
    }

    function prefersReducedMotion() {
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize, { once: true });
    } else {
        initialize();
    }
})();
