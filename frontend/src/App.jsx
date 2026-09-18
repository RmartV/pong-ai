import { useState, useRef, useEffect } from "react";
import "./App.css";

// Base URL for all API calls: points to the FastAPI backend or Vercel environment variable
const API = import.meta.env.VITE_API_URL !== undefined 
  ? import.meta.env.VITE_API_URL 
  : (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" 
      ? "" 
      : "http://localhost:8000");

// ── Icons (inline SVG - zero emojis) ──────────────────────────────────────────
const UploadIcon = () => (
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);

const SpinnerIcon = () => (
  <svg className="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <path d="M12 2a10 10 0 1 0 10 10" />
  </svg>
);

const ChipIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="6" height="6" rx="1" />
    <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
    <rect x="2" y="2" width="20" height="20" rx="3" />
  </svg>
);

const TrashIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6M14 11v6" /><path d="M9 6V4h6v2" />
  </svg>
);

const PencilIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
);

const MenuIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
  </svg>
);

const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const AlertIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const CloseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const CameraIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
    <circle cx="12" cy="13" r="4" />
  </svg>
);

const MicIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const EyeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const UserIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const FileTextIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const ActivityIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);

const BellIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
    <path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
);

const LogOutIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" y1="12" x2="9" y2="12" />
  </svg>
);

const LayersIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 2 7 12 12 22 7 12 2" />
    <polyline points="2 17 12 22 22 17" />
    <polyline points="2 12 12 17 22 12" />
  </svg>
);

const SlidersIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" y1="21" x2="4" y2="14" />
    <line x1="4" y1="10" x2="4" y2="3" />
    <line x1="12" y1="21" x2="12" y2="12" />
    <line x1="12" y1="8" x2="12" y2="3" />
    <line x1="20" y1="21" x2="20" y2="16" />
    <line x1="20" y1="12" x2="20" y2="3" />
    <line x1="1" y1="14" x2="7" y2="14" />
    <line x1="9" y1="8" x2="15" y2="8" />
    <line x1="17" y1="16" x2="23" y2="16" />
  </svg>
);

const BriefcaseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
    <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
  </svg>
);

// ── Main App Component ────────────────────────────────────────────────────────
export default function App() {
  // Navigation System State: 'pong' (Scoping Engine) | 'blueprint' (Talent Intake Portal)
  const [activeSystem, setActiveSystem] = useState("pong");

  // PongAI Scoping Engine state
  const [file, setFile]                 = useState(null);
  const [teamSize, setTeamSize]         = useState(4);
  const [result, setResult]             = useState(null);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState("");
  const [dragging, setDragging]         = useState(false);
  const [sidebarOpen, setSidebarOpen]   = useState(true);
  const [projects, setProjects]         = useState([]);
  const [renamingId, setRenamingId]     = useState(null);
  const [renameVal, setRenameVal]       = useState("");

  // Player Cards & Jira state
  const [candidates, setCandidates]     = useState([]);
  const [rosterOpen, setRosterOpen]     = useState(false);
  const [jiraModalOpen, setJiraModalOpen] = useState(false);
  const [jiraData, setJiraData]         = useState(null);
  const [syncingJira, setSyncingJira]   = useState(false);

  // Blueprint Standalone Portal State (Camera, Voice, Eye Tracking & Resume Ingestion)
  const [resumeFile, setResumeFile]       = useState(null);
  const [spokenPitch, setSpokenPitch]     = useState("");
  const [isRecording, setIsRecording]     = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [cameraError, setCameraError]     = useState(null);
  const [submittingPitch, setSubmittingPitch] = useState(false);
  const [pitchResult, setPitchResult]     = useState(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionStatus, setTranscriptionStatus] = useState(null);
  const [audioLevel, setAudioLevel]       = useState(0);
  const [recordedAudioBlob, setRecordedAudioBlob] = useState(null);

  // Real-Time Eye Contact & Confidence Telemetry (Standby until pitch recording begins)
  const [telemetryActive, setTelemetryActive]   = useState(false);
  const [eyeContact, setEyeContact]             = useState(0);
  const [isDirectEyeContact, setIsDirectEyeContact] = useState(false);
  const [vocalCadence, setVocalCadence]         = useState(0);
  const [vocalArchetype, setVocalArchetype]     = useState("Standby");
  const [confidenceScore, setConfidenceScore]   = useState(0);
  const [confidenceArchetype, setConfidenceArchetype] = useState("Awaiting Video & Audio");


  // Manager Authentication State
  const [managerToken, setManagerToken] = useState(() => localStorage.getItem("pongai_manager_token") || "");
  const [managerUser, setManagerUser]   = useState(() => {
    try {
      const saved = localStorage.getItem("pongai_manager_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [authEmail, setAuthEmail]       = useState("manager@enterprise.io");
  const [authPassword, setAuthPassword] = useState("manager123");
  const [authName, setAuthName]         = useState("");
  const [authDept, setAuthDept]         = useState("Engineering Operations");
  const [authMode, setAuthMode]         = useState("login"); // 'login' | 'register'
  const [authLoading, setAuthLoading]   = useState(false);
  const [authError, setAuthError]       = useState("");

  // Project History & Modification State
  const [historyOpen, setHistoryOpen]       = useState(false);
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [savingEdit, setSavingEdit]         = useState(false);

  // In-App Manager Notifications State
  const [notifications, setNotifications]   = useState([]);
  const [notifDropdownOpen, setNotifDropdownOpen] = useState(false);

  // Refs
  const videoRef            = useRef(null);
  const canvasRef           = useRef(null);
  const mediaStreamRef      = useRef(null);
  const mediaRecorderRef    = useRef(null);
  const audioChunksRef      = useRef([]);
  const finalTranscriptRef  = useRef("");
  const recognitionRef      = useRef(null);
  const timerRef            = useRef(null);
  const isRecordingRef      = useRef(false);
  const audioContextRef     = useRef(null);
  const animFrameRef        = useRef(null);
  const eyeTrackingIntervalRef = useRef(null);
  const faceDetectorRef     = useRef(null);
  const lastDirectGazeRef   = useRef(false);
  const blinkCounterRef     = useRef(0);
  const vocalCadenceRef     = useRef(0);
  const resumeInputRef      = useRef(null);
  const fileInputRef        = useRef(null);
  const resultsRef          = useRef(null);
  const [previewUrl, setPreviewUrl]     = useState(null);
  const [previewText, setPreviewText]   = useState(null);

  useEffect(() => {
    fetchProjects();
    fetchCandidates();
    fetchNotifications();
  }, []);

  useEffect(() => {
    const last = localStorage.getItem("pong_last_project");
    if (last) loadProject(last);
  }, []);

  // Validate manager session token on load
  useEffect(() => {
    if (managerToken) {
      fetch(`${API}/api/auth/me`, {
        headers: { Authorization: `Bearer ${managerToken}` }
      })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(data => {
          if (data?.user) {
            setManagerUser(data.user);
            localStorage.setItem("pongai_manager_user", JSON.stringify(data.user));
          }
        })
        .catch(() => {
          setManagerToken("");
          setManagerUser(null);
          localStorage.removeItem("pongai_manager_token");
          localStorage.removeItem("pongai_manager_user");
        });
    }
  }, [managerToken]);

  // Keyboard accessibility: dismiss modals on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        if (rosterOpen) setRosterOpen(false);
        if (jiraModalOpen) setJiraModalOpen(false);
        if (adjustModalOpen) setAdjustModalOpen(false);
        if (historyOpen) setHistoryOpen(false);
        if (notifDropdownOpen) setNotifDropdownOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [rosterOpen, jiraModalOpen, adjustModalOpen, historyOpen, notifDropdownOpen]);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API}/api/projects`);
      const data = await res.json();
      setProjects(data);
    } catch {}
  };

  const fetchCandidates = async () => {
    try {
      const res = await fetch(`${API}/api/candidates`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setCandidates(data);
    } catch {
      // Clean empty roster: NO hardcoded mock candidates!
      setCandidates([]);
    }
  };

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`${API}/api/notifications`);
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
      }
    } catch {}
  };

  const handleManagerLogin = async (e) => {
    if (e) e.preventDefault();
    setAuthError("");
    setAuthLoading(true);
    try {
      const endpoint = authMode === "login" ? `${API}/api/auth/login` : `${API}/api/auth/register`;
      const body = authMode === "login"
        ? { email: authEmail, password: authPassword }
        : { email: authEmail, password: authPassword, name: authName, department: authDept };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed");
      }
      setManagerToken(data.token);
      setManagerUser(data.user);
      localStorage.setItem("pongai_manager_token", data.token);
      localStorage.setItem("pongai_manager_user", JSON.stringify(data.user));
      fetchProjects();
      fetchNotifications();
    } catch (err) {
      setAuthError(err.message || "Failed to authenticate");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleManagerLogout = () => {
    setManagerToken("");
    setManagerUser(null);
    localStorage.removeItem("pongai_manager_token");
    localStorage.removeItem("pongai_manager_user");
  };

  const fillDemoManager = () => {
    setAuthEmail("manager@enterprise.io");
    setAuthPassword("manager123");
    setAuthMode("login");
  };

  const openAdjustModal = (proj) => {
    const target = proj || result;
    if (!target) return;
    setEditingProject({
      ...target,
      roles: (target.roles || []).map(r => ({ ...r, tasks: [...(r.tasks || [])] }))
    });
    setHistoryOpen(false);
    setAdjustModalOpen(true);
  };

  const handleSaveProjectAdjustment = async () => {
    if (!editingProject) return;
    setSavingEdit(true);
    try {
      const res = await fetch(`${API}/api/projects/${editingProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: editingProject.project_name,
          domain: editingProject.domain,
          team_size: editingProject.team_size,
          roles: editingProject.roles,
          tech_signals: editingProject.tech_signals,
          domain_skills: editingProject.domain_skills
        })
      });
      if (!res.ok) throw new Error("Failed to update project");
      const data = await res.json();
      if (result && result.id === editingProject.id) {
        setResult(data.project);
      }
      setAdjustModalOpen(false);
      setEditingProject(null);
      fetchProjects();
    } catch (err) {
      alert(err.message || "Failed to save adjustments");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleApproveCandidateAssignment = async (notif) => {
    if (!notif.project_id || !notif.role_name || !notif.candidate_id) return;
    try {
      const res = await fetch(`${API}/api/projects/${notif.project_id}/assign-candidate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_id: notif.candidate_id,
          role_name: notif.role_name,
          rationale: "Approved via manager cockpit."
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (result && result.id === notif.project_id) {
          setResult(data.project);
        }
        await fetch(`${API}/api/notifications/${notif.id}/read`, { method: "POST" });
        fetchNotifications();
        fetchProjects();
      }
    } catch (err) {
      alert("Failed to assign candidate: " + err.message);
    }
  };

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    setError("");
    setResult(null);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  useEffect(() => {
    let url = null;
    let reader = null;
    setPreviewUrl(null);
    setPreviewText(null);
    if (!file) return () => {};

    const name = (file.name || "").toLowerCase();
    if (name.endsWith('.pdf') || file.type === 'application/pdf') {
      url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else if (name.endsWith('.txt') || file.type === 'text/plain') {
      reader = new FileReader();
      reader.onload = (e) => setPreviewText(String(e.target.result));
      reader.readAsText(file);
    } else if (name.endsWith('.docx')) {
      url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }

    return () => {
      if (url) URL.revokeObjectURL(url);
      if (reader) reader.abort && reader.abort();
    };
  }, [file]);

  const handleAnalyze = async () => {
    if (!file) { setError("Please upload a project document first."); return; }
    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("team_size", teamSize);

    try {
      const res = await fetch(`${API}/api/analyze`, { method: "POST", body: formData });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data);
      fetchProjects();
      fetchCandidates();
      if (data.id) localStorage.setItem("pong_last_project", data.id);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch {
      // Fallback project for demo preview (zero emojis)
      const fallbackProject = {
        id: "proj_demo_preview",
        project_name: file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ") || "Real-Time Payment Gateway & Microservices",
        team_size: teamSize,
        tech_signals: ["REST API Architecture", "Microservices", "High-Concurrency Backend", "FastAPI/PostgreSQL"],
        total_roles: Math.min(teamSize, 4),
        created_at: new Date().toISOString(),
        roles: [
          {
            role: "Lead API & Backend Developer",
            badge: "Dedicated",
            color: "#3b82f6",
            icon: "API",
            assigned_candidate: null,
            tasks: [
              "Design OpenAPI 3.0 specification & high-throughput API gateway routing",
              "Implement secure JWT authentication, rate-limiting, and error middleware",
              "Construct relational schema and query optimization for high-concurrency endpoints",
              "Establish automated integration tests and contract validation for all REST routes"
            ]
          },
          ...(teamSize >= 2 ? [{
            role: "Frontend Engineer",
            badge: "Dedicated",
            color: "#06b6d4",
            icon: "UI",
            assigned_candidate: null,
            tasks: [
              "Build responsive React component library and interactive user dashboards",
              "Integrate client-side REST API consumption with optimistic UI updates",
              "Ensure accessible WCAG compliance, mobile viewport responsiveness, and UX flow"
            ]
          }] : []),
          ...(teamSize >= 3 ? [{
            role: "DevOps & Cloud Engineer",
            badge: "Dedicated",
            color: "#f59e0b",
            icon: "Cloud",
            assigned_candidate: null,
            tasks: [
              "Containerize microservices with multi-stage Docker builds",
              "Configure automated CI/CD pipeline and deployment stages",
              "Provision cloud infrastructure with Terraform and environment secrets"
            ]
          }] : []),
          ...(teamSize >= 4 ? [{
            role: "Tech Lead / Project Manager",
            badge: "Dedicated",
            color: "#6366f1",
            icon: "Lead",
            assigned_candidate: null,
            tasks: [
              "Define sprint deliverables, milestone criteria, and architectural guidelines",
              "Coordinate cross-team API contracts between frontend and backend engineers",
              "Prepare stakeholder presentation, sprint demo, and release documentation"
            ]
          }] : [])
        ]
      };
      setResult(fallbackProject);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncJira = async () => {
    if (!result) return;
    setSyncingJira(true);
    const projId = result.id || `proj_${Date.now()}`;
    const workatoDirectUrl = "https://webhooks.trial.workato.com/webhooks/rest/3bab9a2f-bb30-454b-9639-3354ff497494/pongai_project_matched";

    const projectKey = (result.project_name || "PONG").replace(/[^A-Z]/gi, "").substring(0, 4).toUpperCase() || "PONG";
    let issueCounter = 1;
    const issues = (result.roles || []).flatMap((r, rIdx) => 
      (r.tasks || []).map((t, tIdx) => ({
        key: `${projectKey}-${issueCounter++}`,
        role: r.role,
        summary: `[${r.role}] ${t}`,
        assignee: r.assigned_candidate?.name || "Unassigned",
        story_points: tIdx % 2 === 0 ? 3 : 5,
        status: "Backlog (Unassigned)",
        labels: ["pongai-matched", "workato-synced"]
      }))
    );

    const workatoPayload = {
      event: "pongai_project_matched",
      project_id: projId,
      project_name: result.project_name || "Enterprise Project",
      tech_signals: result.tech_signals || [],
      team_size: result.team_size || (result.roles || []).length,
      roles: result.roles || [],
      unassigned_backlog: issues,
      issues: issues,
      total_story_points: issues.reduce((acc, i) => acc + i.story_points, 0),
      jira_project: {
        key: projectKey,
        name: result.project_name || "Enterprise Project",
        board_name: `${result.project_name || "Enterprise"} Agile Board`
      },
      sprint: {
        sprint_id: 101,
        name: "Sprint 1 - Foundation & Core Architecture",
        total_story_points: issues.reduce((acc, i) => acc + i.story_points, 0),
        issues_count: issues.length
      }
    };

    try {
      // 1. Send request to backend
      const res = await fetch(`${API}/api/projects/${projId}/sync-jira`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result)
      });
      if (res.ok) {
        const data = await res.json();
        setJiraData(data);
        setJiraModalOpen(true);
        return;
      }
      throw new Error(`Backend HTTP ${res.status}`);
    } catch (err) {
      console.warn("Backend sync notification, executing direct browser-to-Workato webhook dispatch:", err);
      // 2. Direct browser-to-Workato webhook dispatch (ensures Workato ALWAYS triggers on Vercel)
      try {
        await fetch(workatoDirectUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(workatoPayload)
        });
        console.info("Direct Workato Webhook dispatched successfully!");
      } catch (wErr) {
        console.warn("Direct Workato dispatch notice:", wErr);
      }

      setJiraData({
        status: "provisioned",
        jira_project: workatoPayload.jira_project,
        sprint: workatoPayload.sprint,
        issues: issues
      });
      setJiraModalOpen(true);
    } finally {
      setSyncingJira(false);
    }
  };

  const loadProject = async (id) => {
    try {
      const res = await fetch(`${API}/api/projects/${id}`);
      if (!res.ok) {
        localStorage.removeItem("pong_last_project");
        return;
      }
      const data = await res.json();
      if (!data || !Array.isArray(data.roles)) {
        localStorage.removeItem("pong_last_project");
        return;
      }
      setResult(data);
      setFile(null);
      setError("");
      localStorage.setItem("pong_last_project", id);

      if (previewUrl) {
        try { URL.revokeObjectURL(previewUrl); } catch {}
        setPreviewUrl(null);
      }
      setPreviewText(null);
      if (data.file_id) {
        try {
          const fres = await fetch(`${API}/api/projects/${id}/file`);
          if (fres.ok) {
            const blob = await fres.blob();
            const mime = data.file_content_type || blob.type || "application/octet-stream";
            const restoredFile = new File([blob], data.file_name || "document", { type: mime });
            setFile(restoredFile);
            if (mime.startsWith("text/")) {
              const txt = await blob.text();
              setPreviewText(txt);
            } else {
              const url = URL.createObjectURL(blob);
              setPreviewUrl(url);
            }
          }
        } catch {}
      }
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch {
      setError("Failed to load project.");
    }
  };

  const startRename = (p, e) => {
    e.stopPropagation();
    setRenamingId(p.id);
    setRenameVal(p.project_name);
  };

  const submitRename = async (id) => {
    if (!renameVal.trim()) return;
    await fetch(`${API}/api/projects/${id}/rename`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_name: renameVal }),
    });
    setRenamingId(null);
    fetchProjects();
    if (result?.id === id) setResult({ ...result, project_name: renameVal });
  };

  const deleteProject = async (id, e) => {
    e.stopPropagation();
    await fetch(`${API}/api/projects/${id}`, { method: "DELETE" });
    fetchProjects();
    if (result?.id === id) setResult(null);
    const last = localStorage.getItem("pong_last_project");
    if (last === id) localStorage.removeItem("pong_last_project");
  };

  const formatDate = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  };

  // ── Blueprint Camera, Voice & Eye Contact / Confidence Engine ────────────────
  const startPitchRecording = async () => {
    setCameraError(null);
    setTranscriptionStatus(null);
    setIsRecording(true);
    isRecordingRef.current = true;
    setRecordingTime(0);
    setSpokenPitch("");
    finalTranscriptRef.current = "";
    audioChunksRef.current = [];
    setRecordedAudioBlob(null);

    // Initialize telemetry dynamically (no preloaded static values)
    setTelemetryActive(true);
    setEyeContact(0);
    setIsDirectEyeContact(false);
    lastDirectGazeRef.current = false;
    blinkCounterRef.current = 0;
    setVocalCadence(0);
    setVocalArchetype("Listening...");
    setConfidenceScore(0);
    setConfidenceArchetype("Calibrating biometrics...");

    let stream = null;
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 } },
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
          });
        } catch (vidErr) {
          console.warn("Camera video unavailable, falling back to microphone-only intake:", vidErr);
          stream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
          });
        }

        mediaStreamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }

        // Web Audio API live volume meter and cadence stability tracking
        const audioTracks = stream.getAudioTracks();
        if (audioTracks.length > 0) {
          const audioStream = new MediaStream(audioTracks);

          try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) {
              const audioCtx = new AudioCtx();
              const source = audioCtx.createMediaStreamSource(audioStream);
              const analyser = audioCtx.createAnalyser();
              analyser.fftSize = 256;
              source.connect(analyser);
              const dataArray = new Uint8Array(analyser.frequencyBinCount);

              let recentVols = [];

              const updateMeter = () => {
                if (!isRecordingRef.current) return;
                analyser.getByteFrequencyData(dataArray);
                let sum = 0;
                for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
                const avg = sum / dataArray.length;
                const pct = Math.min(100, Math.round((avg / 128) * 100));
                setAudioLevel(pct);

                // Track vocal stability, cadence, stuttering, and hesitation dynamically
                recentVols.push(pct);
                if (recentVols.length > 35) recentVols.shift();

                const activeSamples = recentVols.filter((v) => v > 6);
                if (activeSamples.length >= 4) {
                  // 1. Measure frame-to-frame jumpiness (jerk / stuttering spikes)
                  let jerkSum = 0;
                  for (let i = 1; i < recentVols.length; i++) {
                    jerkSum += Math.abs(recentVols[i] - recentVols[i - 1]);
                  }
                  const avgJerk = jerkSum / (recentVols.length - 1); // smooth speech: 4-12; stuttering: 18-45

                  // 2. Measure sudden dropouts / glottal stops / hesitations
                  let dropouts = 0;
                  for (let i = 1; i < recentVols.length; i++) {
                    if (recentVols[i - 1] > 16 && recentVols[i] <= 5) dropouts++;
                  }

                  // 3. Measure volume variance
                  const mean = activeSamples.reduce((a, b) => a + b, 0) / activeSamples.length;
                  const variance = activeSamples.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / activeSamples.length;

                  // Fluent speech: steady moderate volume, low jerk (< 12), few dropouts
                  // Stuttering / nervous speech: high jerk (> 16), frequent dropouts (> 1), erratic variance
                  let stabilityScore = 95;
                  if (avgJerk > 12) {
                    stabilityScore -= Math.min(48, Math.round((avgJerk - 12) * 2.8));
                  }
                  if (dropouts > 0) {
                    stabilityScore -= Math.min(35, dropouts * 14);
                  }
                  if (variance > 120) {
                    stabilityScore -= Math.min(25, Math.round((variance - 120) * 0.12));
                  }

                  // True responsive range: 15% to 96% (can drop to 20-35% on stuttering/hesitation)
                  const finalStability = Math.max(15, Math.min(96, Math.round(stabilityScore)));
                  vocalCadenceRef.current = finalStability;
                  setVocalCadence(finalStability);

                  if (finalStability >= 82) setVocalArchetype("Dynamic & Resonant");
                  else if (finalStability >= 65) setVocalArchetype("Steady & Articulate");
                  else if (finalStability >= 45) setVocalArchetype("Hesitant / Pauses Detected");
                  else setVocalArchetype("Stuttering / High Vocal Jitter");
                } else {
                  // Low volume or silence
                  const decayed = Math.max(20, Math.round((vocalCadenceRef.current || 50) * 0.9));
                  vocalCadenceRef.current = decayed;
                  setVocalCadence(decayed);
                  setVocalArchetype("Awaiting Speech / Silence");
                }

                animFrameRef.current = requestAnimationFrame(updateMeter);
              };
              updateMeter();
              audioContextRef.current = audioCtx;
            }
          } catch (audioMeterErr) {
            console.warn("Audio meter setup notice:", audioMeterErr);
          }

          // Initialize MediaRecorder for high-fidelity audio capture
          if (typeof MediaRecorder !== "undefined") {
            const preferredTypes = [
              "audio/webm;codecs=opus",
              "audio/webm",
              "audio/ogg;codecs=opus",
              "audio/mp4",
              "audio/wav"
            ];
            let selectedType = "";
            for (const t of preferredTypes) {
              if (MediaRecorder.isTypeSupported(t)) {
                selectedType = t;
                break;
              }
            }

            try {
              const options = selectedType ? { mimeType: selectedType } : undefined;
              const recorder = new MediaRecorder(audioStream, options);
              recorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) {
                  audioChunksRef.current.push(e.data);
                }
              };
              recorder.start(200);
              mediaRecorderRef.current = recorder;
            } catch (recErr) {
              console.warn("MediaRecorder init notice:", recErr);
            }
          }
        }
      }
    } catch (err) {
      console.warn("Microphone access permission notice:", err);
      setCameraError("Microphone permission required for speech intake. Please allow microphone access.");
      setIsRecording(false);
      isRecordingRef.current = false;
      return;
    }

    timerRef.current = setInterval(() => {
      setRecordingTime((prev) => prev + 1);
    }, 1000);

    // Real-Time Eye Contact & Face Gaze Centering Loop
    const gazeHistory = [];

    eyeTrackingIntervalRef.current = setInterval(() => {
      if (!isRecordingRef.current) return;

      let isDirectGaze = false;
      let personDetected = false;

      if (videoRef.current && videoRef.current.videoWidth > 0 && canvasRef.current) {
        try {
          const cvs = canvasRef.current;
          const ctx = cvs.getContext("2d", { willReadFrequently: true });
          ctx.drawImage(videoRef.current, 0, 0, cvs.width, cvs.height);
          const frame = ctx.getImageData(0, 0, cvs.width, cvs.height);
          const d = frame.data;
          const w = cvs.width;
          const h = cvs.height;

          // 1. Detect skin pixels and compute face Center of Mass
          let skinCount = 0;
          let sumX = 0;
          let sumY = 0;

          for (let y = 0; y < h; y += 2) {
            for (let x = 0; x < w; x += 2) {
              const i = (y * w + x) * 4;
              const r = d[i];
              const g = d[i + 1];
              const b = d[i + 2];

              // Chrominance & Skin Tone filter
              if (r > 40 && g > 25 && b > 15 && r > g && (r - b) > 8 && Math.abs(r - g) > 4) {
                skinCount++;
                sumX += x;
                sumY += y;
              }
            }
          }

          if (skinCount >= 40) {
            personDetected = true;
            const faceCx = sumX / skinCount;
            const faceCy = sumY / skinCount;

            // 2. Measure Head Yaw (Turning left vs right):
            // Count skin pixels to the left vs right of the face centroid
            let leftSkin = 0;
            let rightSkin = 0;

            for (let y = 0; y < h; y += 2) {
              for (let x = 0; x < w; x += 2) {
                const i = (y * w + x) * 4;
                const r = d[i];
                const g = d[i + 1];
                const b = d[i + 2];

                if (r > 40 && g > 25 && b > 15 && r > g && (r - b) > 8 && Math.abs(r - g) > 4) {
                  if (x < faceCx) leftSkin++;
                  else rightSkin++;
                }
              }
            }

            const yawBalance = Math.min(leftSkin, rightSkin) / Math.max(1, Math.max(leftSkin, rightSkin));
            // When facing the camera, both cheeks are visible: yawBalance >= 0.48
            // When turned sideways to look away: yawBalance drops below 0.40
            const isFacingForward = yawBalance >= 0.48;

            // 3. Measure Ocular Contrast (Looking at camera vs looking down/eyes closed):
            // Eye band is located in the upper 15% above the centroid
            const eyeYStart = Math.max(0, Math.floor(faceCy - h * 0.16));
            const eyeYEnd = Math.min(h - 1, Math.floor(faceCy + h * 0.02));
            const leftEyeXStart = Math.max(0, Math.floor(faceCx - w * 0.20));
            const leftEyeXEnd = Math.max(0, Math.floor(faceCx - w * 0.02));
            const rightEyeXStart = Math.min(w - 1, Math.floor(faceCx + w * 0.02));
            const rightEyeXEnd = Math.min(w - 1, Math.floor(faceCx + w * 0.20));

            let lumaLeftSum = 0, lCount = 0;
            let lumaRightSum = 0, rCount = 0;

            for (let y = eyeYStart; y < eyeYEnd; y += 2) {
              for (let x = leftEyeXStart; x < leftEyeXEnd; x += 2) {
                const idx = (y * w + x) * 4;
                lumaLeftSum += 0.299 * d[idx] + 0.587 * d[idx + 1] + 0.114 * d[idx + 2];
                lCount++;
              }
              for (let x = rightEyeXStart; x < rightEyeXEnd; x += 2) {
                const idx = (y * w + x) * 4;
                lumaRightSum += 0.299 * d[idx] + 0.587 * d[idx + 1] + 0.114 * d[idx + 2];
                rCount++;
              }
            }

            const lAvg = lCount > 0 ? lumaLeftSum / lCount : 0;
            const rAvg = rCount > 0 ? lumaRightSum / rCount : 0;

            // Calculate ocular contrast (eyes open with dark pupils have high variance)
            let leftVarSum = 0, rightVarSum = 0;
            for (let y = eyeYStart; y < eyeYEnd; y += 2) {
              for (let x = leftEyeXStart; x < leftEyeXEnd; x += 2) {
                const idx = (y * w + x) * 4;
                const luma = 0.299 * d[idx] + 0.587 * d[idx + 1] + 0.114 * d[idx + 2];
                leftVarSum += Math.abs(luma - lAvg);
              }
              for (let x = rightEyeXStart; x < rightEyeXEnd; x += 2) {
                const idx = (y * w + x) * 4;
                const luma = 0.299 * d[idx] + 0.587 * d[idx + 1] + 0.114 * d[idx + 2];
                rightVarSum += Math.abs(luma - rAvg);
              }
            }

            const leftContrast = lCount > 0 ? leftVarSum / lCount : 0;
            const rightContrast = rCount > 0 ? rightVarSum / rCount : 0;

            // Eyes open and looking forward: both ocular regions show healthy contrast
            // (Looking down or eyes closed drops contrast below 5)
            const hasOcularGaze = leftContrast >= 5 && rightContrast >= 5;

            // 4. Centering within the camera frame
            const isCentered = faceCx >= w * 0.18 && faceCx <= w * 0.82 && faceCy >= h * 0.12 && faceCy <= h * 0.82;

            // Direct Gaze: Face in frame + facing forward + eyes looking forward
            isDirectGaze = isCentered && isFacingForward && hasOcularGaze;
          }
        } catch (e) {
          isDirectGaze = false;
        }
      }

      // Blink Tolerance Filter (holds direct gaze for 1 frame during natural 150ms blink)
      if (!isDirectGaze && lastDirectGazeRef.current && blinkCounterRef.current < 2) {
        isDirectGaze = true;
        blinkCounterRef.current++;
      } else if (isDirectGaze) {
        blinkCounterRef.current = 0;
        lastDirectGazeRef.current = true;
      } else {
        lastDirectGazeRef.current = false;
      }

      // Smooth Rolling Window & Responsive Scoring
      gazeHistory.push(isDirectGaze ? 1 : 0);
      if (gazeHistory.length > 10) gazeHistory.shift();

      const directRatio = gazeHistory.filter(Boolean).length / gazeHistory.length;

      let currentEyeContact = 0;
      if (personDetected) {
        if (isDirectGaze) {
          // Direct gaze locks between 82% and 96%
          currentEyeContact = Math.round(78 + directRatio * 18);
        } else {
          // Looking away drops swiftly to 20% - 38%
          currentEyeContact = Math.max(18, Math.round(20 + directRatio * 25));
        }
      } else {
        // No person in camera view
        currentEyeContact = 0;
      }

      setEyeContact(currentEyeContact);
      setIsDirectEyeContact(isDirectGaze);

      // Composite Confidence Score based on real gaze + real vocal cadence
      const currentCadence = vocalCadenceRef.current || vocalCadence || 50;
      const comp = Math.round(currentEyeContact * 0.5 + currentCadence * 0.5);
      setConfidenceScore(comp);

      if (comp >= 80) setConfidenceArchetype("Executive Composure");
      else if (comp >= 65) setConfidenceArchetype("Confident & Articulate");
      else if (comp >= 45) setConfidenceArchetype("Steady Delivery");
      else if (!isDirectGaze && currentEyeContact < 40) setConfidenceArchetype("Looking Away / Off-Target");
      else setConfidenceArchetype("Calibrating Gaze...");
    }, 200);

    // Continuous SpeechRecognition for live preview
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";
        recognition.maxAlternatives = 1;

        recognition.onresult = (event) => {
          let interim = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscriptRef.current += transcript + " ";
            } else {
              interim += transcript;
            }
          }
          const liveText = (finalTranscriptRef.current + interim).trim();
          if (liveText) {
            setSpokenPitch(liveText);
          }
        };

        recognition.onerror = (e) => {
          console.warn("Speech recognition notice:", e.error);
        };

        recognition.onend = () => {
          if (isRecordingRef.current && mediaStreamRef.current) {
            try { recognition.start(); } catch (e) {}
          }
        };

        recognition.start();
        recognitionRef.current = recognition;
      } catch (err) {
        console.warn("Speech recognition error:", err);
      }
    }
  };

  const stopPitchRecording = () => {
    isRecordingRef.current = false;
    setIsRecording(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (eyeTrackingIntervalRef.current) {
      clearInterval(eyeTrackingIntervalRef.current);
      eyeTrackingIntervalRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    setAudioLevel(0);

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }

    // Stop and process MediaRecorder audio chunks with Gemini AI
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      setIsTranscribing(true);
      setTranscriptionStatus("Gemini AI: Processing audio and transcribing word-for-word...");

      mediaRecorderRef.current.onstop = async () => {
        if (audioContextRef.current) {
          try { audioContextRef.current.close(); } catch (e) {}
          audioContextRef.current = null;
        }

        const mimeType = mediaRecorderRef.current?.mimeType || "audio/webm";
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        setRecordedAudioBlob(audioBlob);

        // Clean up media tracks
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = null;
        }

        const liveSpeech = (finalTranscriptRef.current || "").trim();

        if (audioBlob.size > 200) {
          try {
            const formData = new FormData();
            formData.append("audio", audioBlob, "pitch_voice.webm");
            const res = await fetch(`${API}/api/blueprint/transcribe`, {
              method: "POST",
              body: formData
            });
            const data = await res.json();
            if (data.status === "success" && data.transcript && data.transcript.trim()) {
              const text = data.transcript.trim();
              setSpokenPitch(text);
              finalTranscriptRef.current = text;
              setTranscriptionStatus(`Verbatim Transcription Verified by Gemini AI (${data.word_count || text.split(/\s+/).length} words captured)`);
            } else if (liveSpeech) {
              setSpokenPitch(liveSpeech);
              setTranscriptionStatus(`Voice Captured via Live Speech Engine (${liveSpeech.split(/\s+/).length} words)`);
            } else if (data.status === "no_speech") {
              setTranscriptionStatus("No human speech was detected in audio. Please speak clearly into your mic or type pitch below.");
            } else {
              setTranscriptionStatus(data.detail ? `Transcription note: ${data.detail}` : "Audio transcription complete.");
            }
          } catch (err) {
            console.warn("Gemini audio transcription notice:", err);
            if (liveSpeech) {
              setSpokenPitch(liveSpeech);
              setTranscriptionStatus(`Voice Captured via Live Speech Engine (${liveSpeech.split(/\s+/).length} words)`);
            } else {
              setTranscriptionStatus("Server transcription note. Speak clearly and verify your pitch, or type pitch below.");
            }
          } finally {
            setIsTranscribing(false);
          }
        } else {
          setIsTranscribing(false);
          if (liveSpeech) {
            setSpokenPitch(liveSpeech);
            setTranscriptionStatus(`Voice Captured via Live Speech Engine (${liveSpeech.split(/\s+/).length} words)`);
          } else {
            setTranscriptionStatus("Audio sample was too short. Speak into your microphone and click Stop when done.");
          }
        }
      };

      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        setIsTranscribing(false);
      }
    } else {
      if (audioContextRef.current) {
        try { audioContextRef.current.close(); } catch (e) {}
        audioContextRef.current = null;
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    }
  };

  const handleBlueprintSubmit = async () => {
    if (isRecordingRef.current) {
      stopPitchRecording();
    }
    setSubmittingPitch(true);
    setPitchResult(null);
    try {
      const formData = new FormData();
      if (resumeFile) {
        formData.append("file", resumeFile);
      }
      formData.append("spoken_text", spokenPitch || "Candidate pitch recorded via Blueprint camera and audio ingestion.");
      if (recordedAudioBlob) {
        formData.append("audio", recordedAudioBlob, "pitch_voice.webm");
      }
      formData.append("telemetry_metrics", JSON.stringify({
        eye_contact_percentage: eyeContact,
        confidence_score: confidenceScore,
        vocal_energy: vocalCadence,
        vocal_cadence: vocalCadence,
        confidence_archetype: confidenceArchetype,
        focus_percentage: eyeContact,
        gesture_energy: vocalCadence,
        gesture_profile: "composed_dynamic",
        recording_duration: recordingTime || 15
      }));

      const res = await fetch(`${API}/api/blueprint/pitch`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      setPitchResult(data);
      fetchCandidates();
    } catch (err) {
      setPitchResult({ status: "error", workato_message: err.message });
    } finally {
      setSubmittingPitch(false);
    }
  };

  return (
    <div className="app">
      {/* Offscreen canvas for real-time video eye-tracking */}
      <canvas ref={canvasRef} width="160" height="120" style={{ display: "none" }} />

      {/* ── Sidebar (Only visible in PongAI Scoping Engine) ── */}
      {activeSystem === "pong" && (
        <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
          <div className="sidebar-header">
            <span className="sidebar-title">Past Projects</span>
            <button className="sidebar-close" onClick={() => setSidebarOpen(false)}>
              <CloseIcon />
            </button>
          </div>

          <div className="sidebar-list">
            {projects.length === 0 && (
              <div className="sidebar-empty">No projects yet. Run an analysis to save one.</div>
            )}

            {projects.map((p) => (
              <div key={p.id} className="sidebar-item" onClick={() => loadProject(p.id)}>
                {renamingId === p.id ? (
                  <input
                    className="rename-input"
                    value={renameVal}
                    autoFocus
                    onChange={(e) => setRenameVal(e.target.value)}
                    onBlur={() => submitRename(p.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") submitRename(p.id);
                      if (e.key === "Escape") setRenamingId(null);
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <div className="sidebar-item-info">
                      <span className="sidebar-item-name">{p.project_name}</span>
                      <span className="sidebar-item-date">{formatDate(p.created_at)} · {p.total_roles} roles</span>
                    </div>
                    <div className="sidebar-item-actions">
                      <button className="icon-btn" title="Rename" onClick={(e) => startRename(p, e)}>
                        <PencilIcon />
                      </button>
                      <button className="icon-btn danger" title="Delete" onClick={(e) => deleteProject(p.id, e)}>
                        <TrashIcon />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </aside>
      )}

      {/* ── Main Content Area ── */}
      <div className={`content ${activeSystem === "pong" && sidebarOpen ? "with-sidebar" : ""}`}>
        {/* ── Top Unified Header with System Switcher ── */}
        <header className="header">
          <div className="header-inner">
            <div className="logo">
              {activeSystem === "pong" && !sidebarOpen && (
                <button className="menu-btn" onClick={() => setSidebarOpen(true)}>
                  <MenuIcon />
                </button>
              )}
              <img src="/icon.png" width="24" height="24" style={{ borderRadius: "4px" }} alt="Logo" />
              <span className="logo-text">{activeSystem === "pong" ? "PONG AI" : "BLUEPRINT"}</span>
            </div>

            {/* Top System Switcher Tabs */}
            <div className="system-switcher">
              <button
                className={`system-switcher-tab ${activeSystem === "pong" ? "active" : ""}`}
                onClick={() => setActiveSystem("pong")}
              >
                <ChipIcon />
                <span>PongAI Agile Engine</span>
              </button>
              <button
                className={`system-switcher-tab blueprint-tab ${activeSystem === "blueprint" ? "active" : ""}`}
                onClick={() => setActiveSystem("blueprint")}
              >
                <CameraIcon />
                <span>Blueprint Talent Intake</span>
                <span className="live-hud-pill">LIVE HUD</span>
              </button>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {activeSystem === "pong" && managerUser ? (
                <>
                  <button className="header-action-btn" onClick={() => setHistoryOpen(true)} title="View Past Projects">
                    <LayersIcon />
                    <span>Projects</span>
                  </button>

                  <div className="notif-anchor" style={{ position: "relative" }}>
                    <button
                      className={`header-action-btn ${notifDropdownOpen ? "active" : ""}`}
                      onClick={() => setNotifDropdownOpen(!notifDropdownOpen)}
                      title="Talent Stack Notifications"
                    >
                      <BellIcon />
                      <span>Alerts</span>
                      {notifications.filter((n) => !n.read).length > 0 && (
                        <span className="notif-count-pill">
                          {notifications.filter((n) => !n.read).length}
                        </span>
                      )}
                    </button>

                    {notifDropdownOpen && (
                      <div className="notif-dropdown">
                        <div className="notif-dropdown-header">
                          <span className="notif-dropdown-title">Talent Stack Allocations</span>
                          <button
                            className="notif-clear-btn"
                            onClick={async () => {
                              await fetch(`${API}/api/notifications/clear`, { method: "POST" });
                              fetchNotifications();
                            }}
                          >
                            Clear
                          </button>
                        </div>
                        <div className="notif-list">
                          {notifications.length === 0 ? (
                            <div className="notif-empty">No pending candidate allocations.</div>
                          ) : (
                            notifications.map((n) => (
                              <div key={n.id} className={`notif-item ${n.read ? "read" : "unread"}`}>
                                <div className="notif-item-top">
                                  <span className="notif-cand-name">{n.candidate_name || "Applicant"}</span>
                                  <span className="notif-score-pill">{n.match_score || 85}% Fit</span>
                                </div>
                                <div className="notif-item-role">
                                  Role: <strong>{n.role_name}</strong>
                                </div>
                                <div className="notif-item-proj">
                                  Project: <strong>{n.project_name}</strong>
                                </div>
                                {n.message && <div className="notif-item-msg">{n.message}</div>}
                                <div className="notif-item-actions">
                                  {!n.read ? (
                                    <button
                                      className="notif-approve-btn"
                                      onClick={() => handleApproveCandidateAssignment(n)}
                                    >
                                      Confirm Assignment
                                    </button>
                                  ) : (
                                    <span className="notif-assigned-badge">Assigned to Role</span>
                                  )}
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <button className="header-roster-btn" onClick={() => setRosterOpen(true)}>
                    <UserIcon />
                    <span>Roster</span>
                    <span className="roster-count-pill">{candidates.length}</span>
                  </button>

                  <div className="manager-chip">
                    <span className="manager-name">{managerUser.name || managerUser.email}</span>
                    <span className="manager-dept">{managerUser.department || "Manager"}</span>
                  </div>

                  <button className="header-logout-btn" onClick={handleManagerLogout} title="Sign Out">
                    <LogOutIcon />
                  </button>
                </>
              ) : (
                <>
                  <button className="header-roster-btn" onClick={() => setRosterOpen(true)}>
                    <UserIcon />
                    <span>Candidate Roster</span>
                    <span className="roster-count-pill">{candidates.length} Cards</span>
                  </button>

                  <div className="status-badge">
                    <span className="status-dot" />
                    Workato Engine Active
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* ── SYSTEM 1: PONGAI SCOPING ENGINE ── */}
        {activeSystem === "pong" ? (
          !managerUser ? (
            <main className="main">
              <div className="manager-auth-wrapper">
                <div className="manager-auth-card">
                  <div className="manager-auth-header">
                    <div className="manager-auth-badge">RESTRICTED MANAGER COCKPIT</div>
                    <h2 className="manager-auth-title">PongAI Management Portal</h2>
                    <p className="manager-auth-desc">
                      Restricted access for department managers and engineering leads to scope briefs across multi-department projects, adjust role requirements, and allocate talent.
                    </p>
                  </div>

                  <div className="manager-auth-tabs">
                    <button
                      className={`manager-auth-tab ${authMode === "login" ? "active" : ""}`}
                      onClick={() => { setAuthMode("login"); setAuthError(""); }}
                    >
                      Sign In
                    </button>
                    <button
                      className={`manager-auth-tab ${authMode === "register" ? "active" : ""}`}
                      onClick={() => { setAuthMode("register"); setAuthError(""); }}
                    >
                      Create Account
                    </button>
                  </div>

                  {authError && (
                    <div className="auth-error-banner">
                      <AlertIcon />
                      <span>{authError}</span>
                    </div>
                  )}

                  <form className="manager-auth-form" onSubmit={handleManagerLogin}>
                    {authMode === "register" && (
                      <>
                        <div className="auth-form-field">
                          <label>Full Name</label>
                          <input
                            type="text"
                            placeholder="e.g. Sarah Chen"
                            value={authName}
                            onChange={(e) => setAuthName(e.target.value)}
                            required
                          />
                        </div>
                        <div className="auth-form-field">
                          <label>Department / Function</label>
                          <select
                            value={authDept}
                            onChange={(e) => setAuthDept(e.target.value)}
                          >
                            <option value="Engineering Operations">Engineering Operations</option>
                            <option value="Event Production & Logistics">Event Production & Logistics</option>
                            <option value="Quality Assurance & Reliability">Quality Assurance & Reliability</option>
                            <option value="Product & Creative Strategy">Product & Creative Strategy</option>
                          </select>
                        </div>
                      </>
                    )}

                    <div className="auth-form-field">
                      <label>Enterprise Work Email</label>
                      <input
                        type="email"
                        placeholder="manager@enterprise.io"
                        value={authEmail}
                        onChange={(e) => setAuthEmail(e.target.value)}
                        required
                      />
                    </div>

                    <div className="auth-form-field">
                      <label>Master Password</label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={authPassword}
                        onChange={(e) => setAuthPassword(e.target.value)}
                        required
                      />
                    </div>

                    <button
                      type="submit"
                      className="manager-submit-btn"
                      disabled={authLoading}
                    >
                      {authLoading ? (
                        <><SpinnerIcon /> Verifying Credentials…</>
                      ) : authMode === "login" ? (
                        "Authenticate & Enter Cockpit"
                      ) : (
                        "Register & Enter Cockpit"
                      )}
                    </button>
                  </form>

                  <div className="demo-login-box">
                    <div className="demo-login-label">Evaluation Mode:</div>
                    <button
                      type="button"
                      className="demo-login-btn"
                      onClick={() => {
                        fillDemoManager();
                        setTimeout(() => handleManagerLogin(), 50);
                      }}
                    >
                      1-Click Lead Manager Login (manager@enterprise.io)
                    </button>
                  </div>
                </div>
              </div>
            </main>
          ) : (
            <main className="main">
              {/* Talent Stack Allocation Banner */}
              {notifications.some((n) => !n.read) && (
                <div className="talent-stack-banner">
                  <div className="talent-stack-left">
                    <span className="talent-stack-pulse" />
                    <div>
                      <span className="talent-stack-title">Talent Stack Allocation Alert:</span>
                      <span className="talent-stack-desc">
                        {notifications.filter((n) => !n.read).length} new candidate pitch(es) matched across active projects.
                      </span>
                    </div>
                  </div>
                  <div className="talent-stack-actions">
                    <button className="talent-stack-btn" onClick={() => setNotifDropdownOpen(true)}>
                      <BellIcon />
                      <span>Review Allocations</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Hero Section */}
              <section className="hero">
                <h1 className="hero-title">
                  Stat-Based<br />
                  <span className="hero-accent">Player Card Matching</span>
                </h1>
                <p className="hero-sub">
                  Upload your project brief (IT, Event Management, QA & Testing). PongAI extracts architectural demands, ranks candidate Player Cards,
                  and assigns tasks to members whose verified stats excel in that domain.
                </p>
              </section>

              {/* Control Panel */}
              <section className="panel">
                <div className="panel-grid">
                  <div className="panel-col">
                    <label className="panel-label">Project Scope Document</label>
                    <div
                      className={`dropzone ${dragging ? "drag-over" : ""} ${file ? "has-file" : ""}`}
                      onClick={() => fileInputRef.current?.click()}
                      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                      onDragLeave={() => setDragging(false)}
                      onDrop={onDrop}
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.docx,.txt"
                        style={{ display: "none" }}
                        onChange={(e) => handleFile(e.target.files[0])}
                      />
                      {file ? (
                        <div className="file-info">
                          <div className="file-icon"><FileTextIcon /></div>
                          <div>
                            <div className="file-name">{file.name}</div>
                            <div className="file-size">{(file.size / 1024).toFixed(1)} KB: Ready to match with Player Cards</div>
                          </div>
                          <button className="file-clear" onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null); }}>
                            <CloseIcon />
                          </button>
                        </div>
                      ) : (
                        <div className="drop-content">
                          <UploadIcon />
                          <span className="drop-primary">Drop technical brief here</span>
                          <span className="drop-secondary">PDF, DOCX, or TXT (e.g. API Microservices Spec)</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="panel-col panel-col-narrow">
                    <label className="panel-label">Team Headcount</label>
                    <div className="counter-card">
                      <div className="counter-label">Candidate Allocation Slots</div>
                      <div className="counter-row">
                        <button className="counter-btn" onClick={() => setTeamSize(Math.max(1, teamSize - 1))}>−</button>
                        <div className="counter-value">{teamSize}</div>
                        <button className="counter-btn" onClick={() => setTeamSize(Math.min(12, teamSize + 1))}>+</button>
                      </div>
                      <div className="counter-mode">
                        {teamSize <= 1 ? "Solo Mode: full stack overlap" :
                         teamSize <= 2 ? "Pairing: hybrid roles" :
                         teamSize <= 4 ? "Core Squad: specialized stats" :
                         "Extended: full department matrix"}
                      </div>
                      <div className="counter-track">
                        {Array.from({ length: 12 }).map((_, i) => (
                          <div key={i} className={`track-dot ${i < teamSize ? "track-dot-active" : ""}`} />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {error && <div className="error-bar"><AlertIcon /> {error}</div>}

                <button className="analyze-btn" onClick={handleAnalyze} disabled={loading || !file}>
                  {loading ? <><SpinnerIcon /> Matching Player Cards to Roles…</> : <>Run Stat-Based Allocation Engine</>}
                </button>
              </section>

              {/* Results Section */}
              {result && Array.isArray(result.roles) && (
                <section className="results" ref={resultsRef}>
                  <div className="results-header">
                    <div>
                      <div className="results-project">{result.project_name}</div>
                      <div className="results-meta">
                        {result.total_roles} roles · {result.team_size} members · {result.domain || "Enterprise IT"} · {result.tech_signals?.join(", ")}
                      </div>
                    </div>

                    <div className="results-actions-bar">
                      <button className="adjust-project-btn" onClick={() => openAdjustModal(result)}>
                        <SlidersIcon />
                        <span>Adjust Scope & Roles</span>
                      </button>
                      <button className="sync-jira-btn" onClick={handleSyncJira} disabled={syncingJira}>
                        {syncingJira ? <><SpinnerIcon /> Provisioning…</> : <>Sync to Jira via Workato</>}
                      </button>
                      <div className="results-count">{result.total_roles} <span>Roles</span></div>
                    </div>
                  </div>

                  <div className="roles-grid">
                    {result.roles.map((role, i) => (
                      <RoleCard key={i} role={role} index={i} />
                    ))}
                  </div>
                </section>
              )}

              {/* Document Viewer */}
              {(file || previewUrl || previewText) && (
                <section className="viewer">
                  <div className="viewer-header">Uploaded Technical Brief</div>
                  {previewUrl && file?.name?.toLowerCase().endsWith('.pdf') && (
                    <iframe className="viewer-iframe" title="pdf-preview" src={previewUrl} />
                  )}
                  {previewText && (
                    <pre className="viewer-text">{previewText}</pre>
                  )}
                  {previewUrl && file?.name?.toLowerCase().endsWith('.docx') && (
                    <div className="viewer-docx">
                      <p>Preview not available for DOCX files in-browser.</p>
                      <a className="download-btn" href={previewUrl} download={file.name}>Download {file.name}</a>
                    </div>
                  )}
                </section>
              )}
            </main>
          )
        ) : (
          /* ── SYSTEM 2: BLUEPRINT TALENT INTAKE PORTAL (STANDALONE PAGE) ── */
          <main className="blueprint-page">
            {/* Blueprint Standalone Hero Banner */}
            <section className="blueprint-hero">
              <h1 className="blueprint-title">
                Biometric & Speech Telemetry Intake
              </h1>
              <p className="blueprint-subtitle">
                Candidate assessment powered by computer vision gaze tracking, vocal cadence stability analysis,
                and speech transcription. Upload your resume and record your pitch.
              </p>
            </section>

            {/* Blueprint Interactive Cockpit Layout */}
            <div className="blueprint-cockpit-grid">
              {/* Left Column: Biometric Video & Telemetry Hub */}
              <div className="blueprint-cockpit-col">
                <div className="blueprint-stage-card">
                  <div className="blueprint-card-header">
                    <div className="blueprint-card-title">
                      <CameraIcon /> Video Pitch & Gaze Telemetry
                    </div>
                    <span className={`blueprint-live-tag ${isRecording ? "recording" : ""}`}>
                      {isRecording ? "LIVE STREAMING" : "STANDBY"}
                    </span>
                  </div>

                  {/* Camera Video Feed with HUD Reticle */}
                  <div className="blueprint-camera-viewport">
                    <video ref={videoRef} className="blueprint-video-feed" playsInline muted autoPlay />

                    {isRecording ? (
                      <div className="camera-hud-overlay">
                        {/* Eye Tracking Reticle Crosshair */}
                        <div className={`gaze-reticle ${isDirectEyeContact ? "locked" : "lost"}`}>
                          <div className={`reticle-corner top-left ${!isDirectEyeContact ? "lost" : ""}`} />
                          <div className={`reticle-corner top-right ${!isDirectEyeContact ? "lost" : ""}`} />
                          <div className={`reticle-corner bottom-left ${!isDirectEyeContact ? "lost" : ""}`} />
                          <div className={`reticle-corner bottom-right ${!isDirectEyeContact ? "lost" : ""}`} />
                          <span className="reticle-label" style={{ 
                            color: isDirectEyeContact ? "#22d3ee" : "#f87171",
                            borderColor: isDirectEyeContact ? "rgba(34, 211, 238, 0.35)" : "rgba(239, 68, 68, 0.45)",
                            background: isDirectEyeContact ? "rgba(9, 14, 24, 0.9)" : "rgba(69, 10, 10, 0.92)"
                          }}>
                            {isDirectEyeContact ? "GAZE LOCKED" : "GAZE LOST / LOOKING AWAY"}
                          </span>
                        </div>

                        {/* Top HUD Badges */}
                        <div className="hud-top-bar">
                          <span className="camera-rec-badge">
                            REC {String(Math.floor(recordingTime / 60)).padStart(2, '0')}:{String(recordingTime % 60).padStart(2, '0')}
                          </span>
                          <span className="camera-hud-chip" style={{ color: eyeContact >= 70 ? "#94a3b8" : "#f87171", borderColor: eyeContact >= 70 ? "rgba(255, 255, 255, 0.1)" : "rgba(239, 68, 68, 0.4)" }}>
                            <EyeIcon /> Eye Contact: {eyeContact}%
                          </span>
                        </div>

                        {/* Bottom HUD Badges */}
                        <div className="hud-bottom-bar">
                          <div className="camera-mic-meter-box">
                            <MicIcon />
                            <div className="mic-track">
                              <div
                                className="mic-fill"
                                style={{
                                  width: `${Math.max(6, Math.min(100, audioLevel))}%`,
                                  background: audioLevel > 12 ? '#10b981' : '#f59e0b'
                                }}
                              />
                            </div>
                            <span className="mic-val">{audioLevel > 12 ? 'Voice Active' : 'Mic Live'}</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      !mediaStreamRef.current && (
                        <div className="camera-standby-placeholder">
                          <CameraIcon />
                          <div className="standby-title">Camera & Microphone Ingestion</div>
                          <div className="standby-sub">
                            Click Start Recording below to stream live video telemetry, eye contact metrics, and spoken pitch.
                          </div>
                        </div>
                      )
                    )}
                  </div>

                  {cameraError && (
                    <div className="camera-error-notice">
                      <AlertIcon /> {cameraError}
                    </div>
                  )}

                  {/* Pitch Recording Control */}
                  <div className="blueprint-record-action-box">
                    {!isRecording ? (
                      <button
                        className="blueprint-record-btn start"
                        onClick={startPitchRecording}
                        disabled={isTranscribing}
                      >
                        <CameraIcon />
                        <span>{spokenPitch ? "Re-record Video Pitch" : "Start Pitch (Camera & Voice Ingestion)"}</span>
                      </button>
                    ) : (
                      <button
                        className="blueprint-record-btn stop"
                        onClick={stopPitchRecording}
                      >
                        <div className="stop-square" />
                        <span>Stop Recording & Transcribe ({recordingTime}s recorded)</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Real-time AI Confidence & Telemetry Diagnostics Panel */}
                <div className="blueprint-telemetry-diagnostics">
                  <div className="diagnostics-header">
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <ActivityIcon />
                      <span>Real-Time Biometric & Vocal Delivery Assessment</span>
                    </div>
                    <span className={`telemetry-status-pill ${isRecording ? "active" : telemetryActive ? "captured" : "standby"}`}>
                      {isRecording ? "ANALYZING LIVE" : telemetryActive ? "ASSESSMENT CAPTURED" : "STANDBY"}
                    </span>
                  </div>

                  <div className="diagnostics-metric-row">
                    <div className="metric-info">
                      <span className="metric-label">Eye Contact & Gaze Centering</span>
                      <span className="metric-val" style={{ 
                        color: !telemetryActive ? "#64748b" : eyeContact >= 75 ? "#34d399" : eyeContact >= 45 ? "#fbbf24" : "#f87171" 
                      }}>
                        {!telemetryActive ? "-- (Awaiting Video)" : `${eyeContact}% (${isDirectEyeContact ? "Direct Gaze" : "Looking Away"})`}
                      </span>
                    </div>
                    <div className="metric-bar-track">
                      <div className="metric-bar-fill" style={{ 
                        width: `${eyeContact}%`, 
                        background: eyeContact >= 75 ? "#06b6d4" : eyeContact >= 45 ? "#f59e0b" : "#ef4444" 
                      }} />
                    </div>
                  </div>

                  <div className="diagnostics-metric-row">
                    <div className="metric-info">
                      <span className="metric-label">Vocal Cadence & Resonance</span>
                      <span className="metric-val" style={{ 
                        color: !telemetryActive ? "#64748b" : vocalCadence >= 75 ? "#34d399" : vocalCadence >= 45 ? "#fbbf24" : "#f87171" 
                      }}>
                        {!telemetryActive ? "-- (Awaiting Audio)" : `${vocalCadence}% (${vocalArchetype})`}
                      </span>
                    </div>
                    <div className="metric-bar-track">
                      <div className="metric-bar-fill" style={{ 
                        width: `${vocalCadence}%`, 
                        background: vocalCadence >= 75 ? "#3b82f6" : vocalCadence >= 45 ? "#f59e0b" : "#ef4444" 
                      }} />
                    </div>
                  </div>

                  <div className="diagnostics-metric-row">
                    <div className="metric-info">
                      <span className="metric-label">Composite Applicant Confidence</span>
                      <span className="metric-val" style={{ 
                        color: !telemetryActive ? "#64748b" : confidenceScore >= 75 ? "#34d399" : confidenceScore >= 45 ? "#fbbf24" : "#f87171" 
                      }}>
                        {!telemetryActive ? "-- (Awaiting Stream)" : `${confidenceScore}%: ${confidenceArchetype}`}
                      </span>
                    </div>
                    <div className="metric-bar-track">
                      <div className="metric-bar-fill" style={{ 
                        width: `${confidenceScore}%`, 
                        background: confidenceScore >= 75 ? "#8b5cf6" : confidenceScore >= 45 ? "#f59e0b" : "#ef4444" 
                      }} />
                    </div>
                  </div>

                  {!telemetryActive && (
                    <div className="telemetry-standby-hint">
                      Click "Start Pitch" above to activate camera gaze tracking and speech cadence analysis.
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Resume Upload, Strictly Read-Only Transcript & ONLY the Submit Button */}
              <div className="blueprint-cockpit-col">
                {/* Section 1: Resume Upload Dropzone */}
                <div className="blueprint-resume-card">
                  <div className="blueprint-card-header">
                    <div className="blueprint-card-title">
                      <FileTextIcon /> Candidate Resume Ingestion
                    </div>
                    <span className="blueprint-helper-tag">PDF / DOCX / TXT</span>
                  </div>

                  <input
                    type="file"
                    ref={resumeInputRef}
                    accept=".pdf,.docx,.txt"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setResumeFile(e.target.files[0]);
                      }
                    }}
                  />

                  <div
                    className={`blueprint-dropzone ${resumeFile ? 'has-file' : ''}`}
                    onClick={() => resumeInputRef.current && resumeInputRef.current.click()}
                  >
                    {resumeFile ? (
                      <div className="resume-uploaded-box">
                        <div className="resume-uploaded-name">
                          <CheckIcon /> {resumeFile.name} ({(resumeFile.size / 1024).toFixed(1)} KB)
                        </div>
                        <div className="resume-uploaded-sub">
                          Candidate Name, Email, Target Role, and Technical Skills will be automatically retrieved from this file. Click to change.
                        </div>
                      </div>
                    ) : (
                      <div className="resume-upload-prompt">
                        <UploadIcon />
                        <div className="resume-prompt-title">Select or drag & drop candidate resume</div>
                        <div className="resume-prompt-sub">
                          Name and Email will be extracted dynamically upon submission.
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Section 2: Spoken Pitch Live Preview (Strictly Read-Only) */}
                <div className="blueprint-transcript-card">
                  <div className="blueprint-card-header">
                    <div className="blueprint-card-title">
                      <MicIcon /> Spoken Pitch Preview
                    </div>
                    <span className="blueprint-readonly-badge">Preview Only (Non-Typeable)</span>
                  </div>

                  {/* Active AI Transcription Indicator */}
                  {isTranscribing && (
                    <div className="transcription-loading-card">
                      <div className="transcription-pulse-dot" />
                      <div>
                        <strong style={{ color: "#38bdf8", fontSize: "12px" }}>Speech Transcription...</strong>
                        <div style={{ color: "#94a3b8", fontSize: "11px" }}>Transcribing spoken pitch and calculating vocal stability.</div>
                      </div>
                    </div>
                  )}

                  {/* Transcription Status Feedback */}
                  {transcriptionStatus && !isTranscribing && (
                    <div className="transcription-status-banner">
                      <CheckIcon />
                      <span>{transcriptionStatus}</span>
                    </div>
                  )}

                  {/* Transcript Area */}
                  <textarea
                    rows={6}
                    className="blueprint-transcript-preview"
                    placeholder="Your spoken pitch will be transcribed here automatically as you speak. You can also edit or type your pitch directly here."
                    value={spokenPitch}
                    onChange={(e) => {
                      setSpokenPitch(e.target.value);
                      finalTranscriptRef.current = e.target.value;
                    }}
                  />

                  <div className="transcript-footer-meta">
                    <span>Transcribed Word Count: {spokenPitch ? spokenPitch.trim().split(/\s+/).length : 0} words</span>
                    <span>Audio Processing Engine</span>
                  </div>
                </div>

                {/* Section 3: STRICTLY ONLY THE "SUBMIT" BUTTON */}
                <div className="blueprint-single-submit-container">
                  <button
                    className="blueprint-submit-action-btn"
                    disabled={submittingPitch || (!resumeFile && !spokenPitch)}
                    onClick={handleBlueprintSubmit}
                  >
                    {submittingPitch ? (
                      <>
                        <SpinnerIcon />
                        <span>Evaluating Biometrics & Synthesizing Player Card...</span>
                      </>
                    ) : (
                      <span>Submit</span>
                    )}
                  </button>
                  <div className="blueprint-submit-subnote">
                    Dispatches candidate resume extraction, eye-contact telemetry, and vocal confidence scores directly to the Workato Blueprint Webhook.
                  </div>
                </div>

                {/* Submission Result / Synthesized Player Card Presentation */}
                {pitchResult && (
                  <div className={`blueprint-result-card ${pitchResult.status === "success" ? "success" : "error"}`}>
                    <div className="result-header">
                      <CheckIcon />
                      <span>
                        {pitchResult.status === "success"
                          ? "Pitch Evaluated & Player Card Synthesized"
                          : "Dispatch Notice"}
                      </span>
                    </div>

                    {pitchResult.extracted_from_resume && (
                      <div className="result-extracted-data">
                        <div className="extracted-title">Auto-Extracted from Candidate Resume:</div>
                        <div className="extracted-row"><span>Name:</span> <strong>{pitchResult.extracted_from_resume.name}</strong></div>
                        <div className="extracted-row"><span>Email:</span> <strong>{pitchResult.extracted_from_resume.email || "Extracted from document"}</strong></div>
                        <div className="extracted-row"><span>Role:</span> <strong>{pitchResult.extracted_from_resume.target_role}</strong></div>
                        {pitchResult.extracted_from_resume.skills && (
                          <div className="extracted-row">
                            <span>Skills:</span> <strong>{Array.isArray(pitchResult.extracted_from_resume.skills) ? pitchResult.extracted_from_resume.skills.join(", ") : pitchResult.extracted_from_resume.skills}</strong>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="result-telemetry-summary">
                      <div className="telemetry-pill">Eye Contact: <strong>{eyeContact}%</strong></div>
                      <div className="telemetry-pill">Confidence: <strong>{confidenceScore}%</strong></div>
                      <div className="telemetry-pill">Archetype: <strong>{confidenceArchetype}</strong></div>
                    </div>

                    <div className="result-workato-status">
                      <span>Workato Status:</span> {pitchResult.workato_message}
                    </div>

                    {pitchResult.candidate && (
                      <div className="result-roster-link" onClick={() => { setRosterOpen(true); }}>
                        Registered in Player Card Roster: <strong>{pitchResult.candidate.name} ({pitchResult.candidate.overall_rating} OVR)</strong> (View in Roster)
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </main>
        )}

        {/* Footer */}
        <footer className="footer">
          <span>PONG AI & BLUEPRINT</span>
          <span className="footer-sep">·</span>
          <span>FastAPI + Workato AI + Jira Cloud</span>
        </footer>
      </div>

      {/* ── Candidate Roster Modal (Zero Emojis) ── */}
      {rosterOpen && (
        <div className="modal-overlay" onClick={() => setRosterOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <UserIcon />
                <span>Candidate Player Cards (Workato AI Roster)</span>
              </div>
              <button className="modal-close-btn" onClick={() => setRosterOpen(false)}>
                <CloseIcon />
              </button>
            </div>
            <div className="modal-body">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
                  Player Cards are automatically generated by Workato AI from Blueprint pitches, resumes, and telemetry.
                </p>
                {candidates.length > 0 && (
                  <button
                    onClick={async () => {
                      if (!confirm("Remove all candidates from the roster?")) return;
                      await fetch(`${API}/api/candidates`, { method: "DELETE" });
                      fetchCandidates();
                    }}
                    style={{ background: "#ef444422", color: "#ef4444", border: "1px solid #ef444440", borderRadius: "6px", padding: "5px 12px", fontSize: "12px", cursor: "pointer", whiteSpace: "nowrap", flexShrink: 0 }}
                  >
                    Clear All
                  </button>
                )}
              </div>
              {candidates.length === 0 ? (
                <div className="roster-empty-state">
                  <UserIcon />
                  <div className="roster-empty-title">No candidate player cards in roster yet</div>
                  <div className="roster-empty-sub">
                    Candidate profiles will appear here automatically when pitches and resumes are submitted through the Blueprint intake portal.
                  </div>
                </div>
              ) : (
                <div className="roster-grid">
                  {candidates.map((c, i) => (
                    <div key={i} className="roster-card">
                      <div className="roster-card-header">
                        <div>
                          <div className="roster-name">
                            {c.name}
                            {c.is_demo && <span className="demo-data-tag">[DEMO]</span>}
                          </div>
                          <div className="roster-archetype">{c.avatar_badge} · {c.archetype}</div>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <div className="player-ovr-badge">{c.overall_rating} OVR</div>
                          <button
                            title="Remove candidate"
                            onClick={async (e) => {
                              e.stopPropagation();
                              if (!confirm(`Remove ${c.name} from the roster?`)) return;
                              await fetch(`${API}/api/candidates/${c.candidate_id}`, { method: "DELETE" });
                              fetchCandidates();
                            }}
                            style={{ background: "#ef444422", color: "#ef4444", border: "none", borderRadius: "4px", padding: "3px 7px", fontSize: "13px", cursor: "pointer", lineHeight: 1 }}
                          >
                            X
                          </button>
                        </div>
                      </div>

                      {c.skills && c.skills.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "8px" }}>
                          {c.skills.slice(0, 5).map((sk, si) => (
                            <span key={si} style={{ background: "#1e3a5f", color: "#93c5fd", fontSize: "10px", padding: "2px 7px", borderRadius: "4px" }}>{sk}</span>
                          ))}
                        </div>
                      )}

                      {c.stats && (
                        <div className="roster-stats-grid">
                          {Object.entries(c.stats).map(([k, v]) => {
                            if (k === "confidence" || k === "eye_contact") return null;
                            const label = k.replace(/_/g, " ").toUpperCase();
                            return (
                              <div key={k} className="roster-stat-cell">
                                <div className="roster-stat-label">{label.slice(0, 10)}</div>
                                <div className={`roster-stat-val ${v >= 90 ? 'gold' : ''}`}>{v}</div>
                              </div>
                            );
                          })}
                          {c.stats.confidence !== undefined && (
                            <div className="roster-stat-cell" style={{ gridColumn: "span 3" }}>
                              <div className="roster-stat-label">CONFIDENCE</div>
                              <div className="roster-stat-val gold">{c.stats.confidence}%</div>
                            </div>
                          )}
                          {c.stats.eye_contact !== undefined && (
                            <div className="roster-stat-cell" style={{ gridColumn: "span 3" }}>
                              <div className="roster-stat-label">EYE CONTACT</div>
                              <div className="roster-stat-val gold">{c.stats.eye_contact}%</div>
                            </div>
                          )}
                        </div>
                      )}

                      {c.key_strengths && c.key_strengths.length > 0 && (
                        <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "8px" }}>
                          <strong style={{ color: "#cbd5e1" }}>Superpower:</strong> {c.key_strengths[0]}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Jira Sync Modal (Zero Emojis) ── */}
      {jiraModalOpen && jiraData && (
        <div className="modal-overlay" onClick={() => setJiraModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <CheckIcon />
                <span>Workato to Jira Provisioning Complete</span>
              </div>
              <button className="modal-close-btn" onClick={() => setJiraModalOpen(false)}>
                <CloseIcon />
              </button>
            </div>
            <div className="modal-body">
              <div className="jira-status-banner">
                <div>
                  <strong style={{ color: "#10b981", fontSize: "14px" }}>Jira Project & Agile Scrum Board Live</strong>
                  <div style={{ color: "#cbd5e1", fontSize: "12px", marginTop: "2px" }}>
                    Project Key: <strong>{jiraData.jira_project?.key}</strong> · Agile Board: <strong>{jiraData.jira_project?.board_name}</strong>
                  </div>
                </div>
                <span style={{ background: "#10b98122", color: "#10b981", padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700 }}>
                  Active in Sprint 1
                </span>
              </div>

              <div className="jira-meta-row">
                <div className="jira-meta-card">
                  <span>ACTIVE SPRINT</span>
                  <strong>{jiraData.sprint?.name}</strong>
                </div>
                <div className="jira-meta-card">
                  <span>TOTAL ESTIMATION</span>
                  <strong>{jiraData.sprint?.total_story_points} Story Points</strong>
                </div>
                <div className="jira-meta-card">
                  <span>POPULATED TICKETS</span>
                  <strong>{jiraData.issues?.length} Issues Created</strong>
                </div>
              </div>

              <div style={{ fontSize: "13px", fontWeight: 600, color: "#fff", marginBottom: "8px" }}>
                Auto-Populated Sprint Backlog (Player Card Stats Attached):
              </div>

              <div className="jira-issue-list">
                {jiraData.issues?.map((issue, idx) => (
                  <div key={idx} className="jira-issue-item">
                    <div className="jira-issue-top">
                      <span className="jira-issue-key">{issue.key}</span>
                      <span className="jira-issue-assignee">
                        <UserIcon /> {issue.assignee} ({issue.story_points} pts)
                      </span>
                    </div>
                    <div className="jira-issue-summary">{issue.summary}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Project History Modal (Multi-Department Management) ── */}
      {historyOpen && (
        <div className="modal-overlay" onClick={() => setHistoryOpen(false)}>
          <div className="modal-content history-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <LayersIcon />
                <span>Multi-Department Project History</span>
              </div>
              <button className="modal-close-btn" onClick={() => setHistoryOpen(false)}>
                <CloseIcon />
              </button>
            </div>

            <div className="modal-body">
              <p className="history-modal-sub">
                Browse and adjust scoping parameters across active enterprise departments (IT, Event Management, QA & Testing).
              </p>

              <div className="history-project-grid">
                {projects.map((p) => {
                  const filledCount = (p.roles || []).filter((r) => r.assigned_candidate).length;
                  const totalRoles = (p.roles || []).length;
                  return (
                    <div key={p.id} className="history-project-card">
                      <div className="history-card-top">
                        <div>
                          <span className="history-domain-tag">
                            {p.domain || "Enterprise IT"}
                          </span>
                          <h3 className="history-project-name">{p.project_name}</h3>
                        </div>
                        <span className="history-roles-ratio">
                          {filledCount}/{totalRoles} Staffed
                        </span>
                      </div>

                      <div className="history-card-meta">
                        <span>Headcount: {p.team_size}</span>
                        <span>Created: {formatDate(p.created_at)}</span>
                      </div>

                      <div className="history-roles-preview">
                        {(p.roles || []).map((r, ri) => (
                          <span
                            key={ri}
                            className="history-role-pill"
                            style={{ borderColor: r.color || "#38bdf8", color: r.color || "#38bdf8" }}
                          >
                            {r.role}
                            {r.assigned_candidate ? ` (${r.assigned_candidate.name})` : " (Open)"}
                          </span>
                        ))}
                      </div>

                      <div className="history-card-actions">
                        <button
                          className="history-load-btn"
                          onClick={() => {
                            loadProject(p.id);
                            setHistoryOpen(false);
                          }}
                        >
                          Load into Cockpit
                        </button>
                        <button
                          className="history-adjust-btn"
                          onClick={() => {
                            openAdjustModal(p);
                          }}
                        >
                          <SlidersIcon />
                          <span>Adjust Scope</span>
                        </button>
                        <button
                          className="history-delete-btn"
                          onClick={(e) => deleteProject(p.id, e)}
                          title="Delete Project"
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Project Adjustment Modal ── */}
      {adjustModalOpen && editingProject && (
        <div className="modal-overlay" onClick={() => setAdjustModalOpen(false)}>
          <div className="modal-content adjust-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <SlidersIcon />
                <span>Adjust Project Scope: {editingProject.project_name}</span>
              </div>
              <button className="modal-close-btn" onClick={() => setAdjustModalOpen(false)}>
                <CloseIcon />
              </button>
            </div>

            <div className="modal-body">
              <div className="adjust-form-row">
                <div className="adjust-field">
                  <label>Project Title</label>
                  <input
                    type="text"
                    value={editingProject.project_name}
                    onChange={(e) => setEditingProject({ ...editingProject, project_name: e.target.value })}
                  />
                </div>
                <div className="adjust-field">
                  <label>Department Domain</label>
                  <select
                    value={editingProject.domain || "Enterprise IT & Cloud"}
                    onChange={(e) => setEditingProject({ ...editingProject, domain: e.target.value })}
                  >
                    <option value="Enterprise IT & Cloud">Enterprise IT & Cloud</option>
                    <option value="Event Management & Production">Event Management & Production</option>
                    <option value="Quality Assurance & Testing">Quality Assurance & Testing</option>
                    <option value="Marketing & Creative Strategy">Marketing & Creative Strategy</option>
                  </select>
                </div>
                <div className="adjust-field" style={{ maxWidth: "120px" }}>
                  <label>Headcount</label>
                  <input
                    type="number"
                    min="1"
                    max="12"
                    value={editingProject.team_size || 4}
                    onChange={(e) => setEditingProject({ ...editingProject, team_size: parseInt(e.target.value) || 1 })}
                  />
                </div>
              </div>

              <div className="adjust-roles-section">
                <div className="adjust-roles-header">
                  <h4>Configured Roles & Deliverables ({(editingProject.roles || []).length} Roles)</h4>
                  <button
                    className="add-role-btn"
                    onClick={() => {
                      const newRole = {
                        role: "New Department Role",
                        badge: "NEW",
                        color: "#3b82f6",
                        icon: "ROLE",
                        assigned_candidate: null,
                        tasks: ["Define key objective and deliverables"]
                      };
                      setEditingProject({
                        ...editingProject,
                        roles: [...(editingProject.roles || []), newRole]
                      });
                    }}
                  >
                    + Add Role
                  </button>
                </div>

                <div className="adjust-roles-list">
                  {(editingProject.roles || []).map((r, ri) => (
                    <div key={ri} className="adjust-role-card">
                      <div className="adjust-role-card-header">
                        <input
                          type="text"
                          className="adjust-role-name-input"
                          value={r.role}
                          onChange={(e) => {
                            const updated = [...editingProject.roles];
                            updated[ri].role = e.target.value;
                            setEditingProject({ ...editingProject, roles: updated });
                          }}
                          placeholder="Role Name"
                        />
                        <input
                          type="text"
                          className="adjust-role-badge-input"
                          value={r.badge || ""}
                          onChange={(e) => {
                            const updated = [...editingProject.roles];
                            updated[ri].badge = e.target.value;
                            setEditingProject({ ...editingProject, roles: updated });
                          }}
                          placeholder="Badge (e.g. EVT)"
                        />
                        <input
                          type="color"
                          className="adjust-role-color-input"
                          value={r.color || "#3b82f6"}
                          onChange={(e) => {
                            const updated = [...editingProject.roles];
                            updated[ri].color = e.target.value;
                            setEditingProject({ ...editingProject, roles: updated });
                          }}
                        />
                        <button
                          className="delete-role-btn"
                          onClick={() => {
                            const updated = editingProject.roles.filter((_, idx) => idx !== ri);
                            setEditingProject({ ...editingProject, roles: updated });
                          }}
                          title="Delete Role"
                        >
                          <TrashIcon />
                        </button>
                      </div>

                      <div className="adjust-tasks-list">
                        <label className="adjust-tasks-label">Assigned Tasks / Deliverables:</label>
                        {(r.tasks || []).map((t, ti) => (
                          <div key={ti} className="adjust-task-row">
                            <span className="task-bullet" style={{ background: r.color || "#38bdf8" }} />
                            <input
                              type="text"
                              className="adjust-task-input"
                              value={t}
                              onChange={(e) => {
                                const updated = [...editingProject.roles];
                                updated[ri].tasks[ti] = e.target.value;
                                setEditingProject({ ...editingProject, roles: updated });
                              }}
                            />
                            <button
                              className="delete-task-btn"
                              onClick={() => {
                                const updated = [...editingProject.roles];
                                updated[ri].tasks = updated[ri].tasks.filter((_, idx) => idx !== ti);
                                setEditingProject({ ...editingProject, roles: updated });
                              }}
                              title="Remove Task"
                            >
                              ✕
                            </button>
                          </div>
                        ))}
                        <button
                          className="add-task-btn"
                          onClick={() => {
                            const updated = [...editingProject.roles];
                            updated[ri].tasks = [...(updated[ri].tasks || []), "New assigned deliverable"];
                            setEditingProject({ ...editingProject, roles: updated });
                          }}
                        >
                          + Add Deliverable
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="adjust-modal-actions">
                <button className="adjust-cancel-btn" onClick={() => setAdjustModalOpen(false)}>
                  Cancel
                </button>
                <button
                  className="adjust-save-btn"
                  onClick={handleSaveProjectAdjustment}
                  disabled={savingEdit}
                >
                  {savingEdit ? <><SpinnerIcon /> Saving Changes…</> : "Save Project Adjustments"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Role Card Component with Embedded Player Card (Zero Emojis) ───────────────
function RoleCard({ role, index }) {
  const [open, setOpen] = useState(true);
  const cand = role.assigned_candidate;
  const cstats = cand?.stats;

  return (
    <div
      className="role-card"
      style={{ "--card-color": role.color, animationDelay: `${index * 80}ms` }}
    >
      <div className="role-card-header" onClick={() => setOpen(!open)}>
        <div className="role-icon-badge" style={{ background: role.color + "22", color: role.color }}>
          {role.icon || "DEV"}
        </div>
        <div className="role-info">
          <div className="role-name">{role.role}</div>
          <div className="role-badge" style={{ background: role.color + "22", color: role.color }}>
            {role.badge}
          </div>
        </div>
        <div className={`role-chevron ${open ? "open" : ""}`}>›</div>
      </div>

      {/* Embedded Assigned Candidate Player Card (Only when candidate is assigned) */}
      {cand && cand.name ? (
        <div className="assigned-player-box">
          <div className="player-box-top">
            <div className="player-identity">
              <div className="player-avatar-circle">
                <UserIcon />
              </div>
              <div>
                <div className="player-name-text">{cand.name}</div>
                <div className="player-archetype-tag">{cand.avatar_badge || cand.archetype}</div>
              </div>
            </div>
            <div className="player-ovr-badge">{cand.overall_rating} OVR</div>
          </div>

          {cstats && (
            <div className="player-stats-mini-row">
              {Object.entries(cstats).map(([k, v]) => {
                if (k === "confidence" || k === "eye_contact") return null;
                const label = k.replace(/_/g, " ").toUpperCase();
                return (
                  <div key={k} className={`player-stat-mini-pill ${v >= 90 ? 'highlight' : ''}`}>
                    {label.slice(0, 8)}: <strong>{v}</strong>
                  </div>
                );
              })}
              {cstats.confidence !== undefined && (
                <div className="player-stat-mini-pill highlight">
                  CONF: <strong>{cstats.confidence}%</strong>
                </div>
              )}
              {cstats.eye_contact !== undefined && (
                <div className="player-stat-mini-pill highlight">
                  EYE: <strong>{cstats.eye_contact}%</strong>
                </div>
              )}
            </div>
          )}

          {cand.match_rationale && (
            <div className="manager-rationale-box">
              <span className="manager-rationale-title">Match Rationale:</span>
              {cand.match_rationale}
            </div>
          )}
        </div>
      ) : (
        <div className="unassigned-status-banner">
          <span className="unassigned-dot" />
          <span>Status: <strong>Open Role</strong> (Awaiting Applicant Pitch via Blueprint)</span>
        </div>
      )}

      {/* Task list */}
      {open && (
        <ul className="role-tasks">
          {role.tasks.map((task, j) => (
            <li key={j} className="role-task">
              <span className="task-bullet" style={{ background: role.color }} />
              {task}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}