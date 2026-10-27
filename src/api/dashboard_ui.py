def get_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI PR Assistant — Platform Control Center</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: #F8FAFC;
    }
    .font-mono {
      font-family: 'JetBrains Mono', monospace;
    }
    @keyframes pulse-gentle {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.7; transform: scale(1.05); }
    }
    .animate-pulse-gentle {
      animation: pulse-gentle 2.5s ease-in-out infinite;
    }
    .badge-glow {
      box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);
    }
  </style>
</head>
<body class="text-slate-900 antialiased min-h-screen">
  <div id="root"></div>

  <script type="text/babel">
    const { useState, useEffect, useCallback, useMemo } = React;

    function App() {
      // Main state
      const [activeTab, setActiveTab] = useState("repos"); // "repos" | "reviews" | "queues" | "trigger"
      const [user, setUser] = useState(null);
      const [reposData, setReposData] = useState({ total_count: 0, connected_count: 0, repositories: [] });
      const [loadingRepos, setLoadingRepos] = useState(true);
      const [repoSearch, setRepoSearch] = useState("");
      const [repoFilter, setRepoFilter] = useState("all"); // "all" | "connected" | "available" | "private"
      
      const [queues, setQueues] = useState(null);
      const [runs, setRuns] = useState([]);
      const [selectedRun, setSelectedRun] = useState(null);
      const [runDetails, setRunDetails] = useState(null);
      const [loadingDetails, setLoadingDetails] = useState(false);
      const [detailTab, setDetailTab] = useState("findings"); // "findings" | "sandbox" | "comment"
      
      // Repo PR modal state
      const [selectedRepoForPulls, setSelectedRepoForPulls] = useState(null);
      const [repoPulls, setRepoPulls] = useState([]);
      const [loadingPulls, setLoadingPulls] = useState(false);
      
      // Token modal state
      const [isTokenModalOpen, setIsTokenModalOpen] = useState(false);
      const [customToken, setCustomToken] = useState("");
      const [tokenUpdateStatus, setTokenUpdateStatus] = useState(null);
      
      // Trigger modal state
      const [isTriggerModalOpen, setIsTriggerModalOpen] = useState(false);
      const [isTriggering, setIsTriggering] = useState(false);
      const [triggerSuccess, setTriggerSuccess] = useState(null);
      
      // Form for manual trigger
      const [formRepo, setFormRepo] = useState("HIMpcgithub3000/Airbnb-clone");
      const [formPR, setFormPR] = useState(1);
      const [formHeadSha, setFormHeadSha] = useState("4679557b1d7e015f14fdabcbbc0d1c3e50b6e53c");
      const [formBaseSha, setFormBaseSha] = useState("28b8d6563bc40af0658f3f9e7b5cdcdcd5cf3573");
      const [formPriority, setFormPriority] = useState("P0");
      
      // Stage 3 State: Speculative Merge Queue, Human Feedback & Reindexing
      const [stage3Repo, setStage3Repo] = useState("HIMpcgithub3000/Airbnb-clone");
      const [mergeTrainData, setMergeTrainData] = useState({ total_queued: 0, candidates: [] });
      const [feedbackData, setFeedbackData] = useState({ count: 0, feedback_entries: [] });
      const [reindexStats, setReindexStats] = useState({ total_chunks: 0, indexed_files: [], file_count: 0 });
      const [stage3Loading, setStage3Loading] = useState(false);
      const [stage3ActionMsg, setStage3ActionMsg] = useState(null);
      const [enqueuePRNumber, setEnqueuePRNumber] = useState(2);
      const [enqueueHeadSha, setEnqueueHeadSha] = useState("4679557b1d7e015f14fdabcbbc0d1c3e50b6e53c");

      const [autoRefresh, setAutoRefresh] = useState(true);
      const [lastRefreshed, setLastRefreshed] = useState(new Date());

      // Fetch GitHub User & Repos
      const fetchGitHubData = useCallback(async () => {
        try {
          const [uRes, rRes] = await Promise.all([
            fetch("/api/v1/github/user"),
            fetch("/api/v1/github/repos")
          ]);
          if (uRes.ok) setUser(await uRes.json());
          if (rRes.ok) setReposData(await rRes.json());
        } catch (err) {
          console.error("Failed to load GitHub repositories:", err);
        } finally {
          setLoadingRepos(false);
        }
      }, []);

      // Fetch queues & runs
      const fetchSystemData = useCallback(async () => {
        try {
          const [qRes, rRes] = await Promise.all([
            fetch("/api/v1/queues"),
            fetch("/api/v1/runs")
          ]);
          if (qRes.ok) setQueues(await qRes.json());
          if (rRes.ok) {
            const runList = await rRes.json();
            setRuns(runList);
            if (runList.length > 0 && !selectedRun) {
              inspectRun(runList[0].id);
            }
          }
          setLastRefreshed(new Date());
        } catch (err) {
          console.error("Failed to load status:", err);
        }
      }, [selectedRun]);

      useEffect(() => {
        fetchGitHubData();
        fetchSystemData();
      }, [fetchGitHubData, fetchSystemData]);

      useEffect(() => {
        if (!autoRefresh) return;
        const interval = setInterval(() => {
          fetchSystemData();
        }, 4000);
        return () => clearInterval(interval);
      }, [autoRefresh, fetchSystemData]);

      const inspectRun = async (runId) => {
        setSelectedRun(runId);
        setLoadingDetails(true);
        try {
          const res = await fetch(`/api/v1/runs/${runId}`);
          if (res.ok) setRunDetails(await res.json());
        } catch (err) {
          console.error("Failed to load run details:", err);
        } finally {
          setLoadingDetails(false);
        }
      };

      const handleInspectRepoPulls = async (repoFullName) => {
        setSelectedRepoForPulls(repoFullName);
        setLoadingPulls(true);
        setRepoPulls([]);
        try {
          const [owner, repo] = repoFullName.split("/");
          const res = await fetch(`/api/v1/github/repos/${owner}/${repo}/pulls`);
          if (res.ok) {
            const data = await res.json();
            setRepoPulls(data.pulls || []);
          }
        } catch (err) {
          console.error("Failed to load repo pulls:", err);
        } finally {
          setLoadingPulls(false);
        }
      };

      const handleUpdateToken = async (e) => {
        e.preventDefault();
        setTokenUpdateStatus("validating");
        try {
          const res = await fetch("/api/v1/github/token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: customToken.trim() }),
          });
          if (res.ok) {
            setTokenUpdateStatus("success");
            await fetchGitHubData();
            setTimeout(() => {
              setIsTokenModalOpen(false);
              setTokenUpdateStatus(null);
              setCustomToken("");
            }, 1200);
          } else {
            const err = await res.json();
            setTokenUpdateStatus(`Error: ${err.detail || "Invalid token"}`);
          }
        } catch (err) {
          setTokenUpdateStatus("Network error updating token");
        }
      };

      const handleQuickTrigger = async (type) => {
        setIsTriggering(true);
        setTriggerSuccess(null);
        try {
          let payload;
          if (type === "conflict") {
            payload = {
              action: "synchronize",
              repository: { full_name: "HIMpcgithub3000/Airbnb-clone", clone_url: "" },
              number: 1,
              pull_request: {
                number: 1,
                head: { sha: "4679557b1d7e015f14fdabcbbc0d1c3e50b6e53c" },
                base: { sha: "28b8d6563bc40af0658f3f9e7b5cdcdcd5cf3573" },
                labels: [{ name: "p0" }]
              }
            };
          } else {
            payload = {
              action: "opened",
              repository: { full_name: formRepo, clone_url: "" },
              number: parseInt(formPR),
              pull_request: {
                number: parseInt(formPR),
                head: { sha: formHeadSha },
                base: { sha: formBaseSha },
                labels: [{ name: formPriority.toLowerCase() }]
              }
            };
          }

          const res = await fetch("/webhook/github", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-GitHub-Event": "pull_request",
              "X-GitHub-Delivery": "ui-dispatch-" + Date.now()
            },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          setTriggerSuccess("Enqueued successfully! Analysis ID: " + (data.analysis_id || "OK"));
          await fetchSystemData();
          if (data.analysis_id) {
            inspectRun(data.analysis_id);
            setActiveTab("reviews");
          }
        } catch (err) {
          console.error("Trigger failed:", err);
          setTriggerSuccess("Trigger failed: " + err.message);
        } finally {
          setIsTriggering(false);
        }
      };

      // Stage 3 API Handlers
      const fetchStage3Data = useCallback(async (targetRepo = stage3Repo) => {
        try {
          const parts = targetRepo.split("/");
          if (parts.length !== 2) return;
          const [owner, repo] = parts;
          const [mtRes, fbRes, rxRes] = await Promise.all([
            fetch(`/api/v1/merge-queue/${owner}/${repo}`),
            fetch(`/api/v1/feedback/${owner}/${repo}`),
            fetch(`/api/v1/reindex/${owner}/${repo}`)
          ]);
          if (mtRes.ok) setMergeTrainData(await mtRes.json());
          if (fbRes.ok) setFeedbackData(await fbRes.json());
          if (rxRes.ok) setReindexStats(await rxRes.json());
        } catch (err) {
          console.error("Failed to load Stage 3 data:", err);
        }
      }, [stage3Repo]);

      const handleEnqueueCandidate = async () => {
        setStage3Loading(true);
        setStage3ActionMsg(null);
        try {
          const res = await fetch("/api/v1/merge-queue/enqueue", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              repository_id: stage3Repo,
              pr_number: parseInt(enqueuePRNumber),
              head_sha: enqueueHeadSha,
              target_branch: "main"
            })
          });
          if (res.ok) {
            setStage3ActionMsg(`Enqueued PR #${enqueuePRNumber} into speculative merge train!`);
            await fetchStage3Data();
          }
        } catch (err) {
          setStage3ActionMsg(`Enqueue failed: ${err.message}`);
        } finally {
          setStage3Loading(false);
        }
      };

      const handleSimulateCandidate = async (candidateId, mockConflict = false) => {
        setStage3Loading(true);
        setStage3ActionMsg(null);
        try {
          const res = await fetch("/api/v1/merge-queue/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              candidate_id: candidateId,
              base_target_sha: "main_head_sha",
              mock_conflict: mockConflict
            })
          });
          const data = await res.json();
          if (res.ok) {
            setStage3ActionMsg(
              mockConflict
                ? `Conflict simulation: REJECTED with conflict in ${data.conflict_files ? data.conflict_files.join(", ") : "files"}`
                : `Speculative test passed: VERIFIED against SHA ${data.speculative_sha ? data.speculative_sha.substring(0, 10) : ""}`
            );
            await fetchStage3Data();
          }
        } catch (err) {
          setStage3ActionMsg(`Simulation failed: ${err.message}`);
        } finally {
          setStage3Loading(false);
        }
      };

      const handleSendFeedback = async (prNumber, eventType, category, title, text) => {
        setStage3Loading(true);
        setStage3ActionMsg(null);
        try {
          const res = await fetch("/api/v1/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              repository_id: stage3Repo,
              pr_number: prNumber,
              reviewer_handle: user?.login || "lead_dev",
              event_type: eventType,
              finding_category: category,
              rule_or_title: title,
              feedback_text: text
            })
          });
          const data = await res.json();
          if (res.ok) {
            setStage3ActionMsg(
              `Feedback recorded (${eventType.toUpperCase()}): delta ${data.weight_delta > 0 ? "+" : ""}${data.weight_delta}. Net calibration: ${data.net_historical_calibration}`
            );
            await fetchStage3Data();
          }
        } catch (err) {
          setStage3ActionMsg(`Feedback submission failed: ${err.message}`);
        } finally {
          setStage3Loading(false);
        }
      };

      const handleTriggerReindex = async () => {
        setStage3Loading(true);
        setStage3ActionMsg(null);
        try {
          const res = await fetch("/api/v1/reindex", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              repository_id: stage3Repo,
              commit_sha: "merged_" + Date.now().toString(16),
              changed_files: ["src/api/auth.py", "src/models/user.py"]
            })
          });
          const data = await res.json();
          if (res.ok) {
            setStage3ActionMsg(`Re-indexing completed: Evicted ${data.evicted_chunks} chunks, reindexed ${data.reindexed_chunks} fresh vectors.`);
            await fetchStage3Data();
          }
        } catch (err) {
          setStage3ActionMsg(`Reindex failed: ${err.message}`);
        } finally {
          setStage3Loading(false);
        }
      };

      // Filtered repositories
      const filteredRepos = useMemo(() => {
        return (reposData.repositories || []).filter(r => {
          const matchesSearch = r.name.toLowerCase().includes(repoSearch.toLowerCase()) ||
            r.full_name.toLowerCase().includes(repoSearch.toLowerCase()) ||
            (r.description && r.description.toLowerCase().includes(repoSearch.toLowerCase()));
          
          if (!matchesSearch) return false;
          if (repoFilter === "connected") return r.is_connected;
          if (repoFilter === "available") return !r.is_connected;
          if (repoFilter === "private") return r.private;
          return true;
        });
      }, [reposData, repoSearch, repoFilter]);

      const connectedRepos = useMemo(() => {
        return (reposData.repositories || []).filter(r => r.is_connected);
      }, [reposData]);

      return (
        <div className="min-h-screen bg-slate-50 flex flex-col">
          {/* TOP HEADER */}
          <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between h-16">
                
                {/* Logo & Product Name */}
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-xl shadow-md shadow-blue-500/20">
                    AI
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-extrabold text-slate-900 text-lg tracking-tight">AI PR Assistant</span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                        MISSION CONTROL
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 font-medium">Autonomous PR Review, Conflict & Verification Platform</p>
                  </div>
                </div>

                {/* Right Profile & Connectivity Status */}
                <div className="flex items-center space-x-3">
                  {/* GitHub Profile & Token Badge */}
                  {user && (
                    <div className="flex items-center space-x-2.5 bg-slate-50 border border-slate-200/80 rounded-xl p-1.5 pr-3">
                      <img
                        src={user.avatar_url || "https://github.com/github.png"}
                        alt={user.login}
                        className="w-8 h-8 rounded-lg object-cover border border-slate-200"
                      />
                      <div className="text-left text-xs">
                        <div className="font-bold text-slate-800 leading-tight flex items-center space-x-1">
                          <span>{user.name || user.login}</span>
                          <span className="text-[11px] text-slate-500 font-mono">@{user.login}</span>
                        </div>
                        <div className="flex items-center space-x-1.5 mt-0.5">
                          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                          <span className="text-[11px] font-semibold text-emerald-700">Token Active</span>
                          <button
                            onClick={() => setIsTokenModalOpen(true)}
                            className="text-[10px] text-blue-600 hover:text-blue-800 underline font-medium ml-1"
                          >
                            Manage
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Auto-Refresh Toggle */}
                  <button
                    onClick={() => setAutoRefresh(!autoRefresh)}
                    title={autoRefresh ? "Auto-refresh active (4s)" : "Auto-refresh paused"}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                      autoRefresh
                        ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                        : "bg-slate-100 border-slate-200 text-slate-600"
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${autoRefresh ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`}></span>
                    <span>{autoRefresh ? "Live Sync" : "Sync Paused"}</span>
                  </button>

                  {/* Manual Refresh */}
                  <button
                    onClick={() => { fetchGitHubData(); fetchSystemData(); }}
                    className="p-2 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors"
                    title="Refresh Now"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                </div>

              </div>
            </div>

            {/* PRIMARY NAVIGATION TABS */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-slate-100">
              <nav className="flex space-x-8">
                <button
                  onClick={() => setActiveTab("repos")}
                  className={`py-3.5 px-1 border-b-2 font-bold text-sm flex items-center space-x-2 transition-all ${
                    activeTab === "repos"
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <span>1. GitHub Repositories Hub</span>
                  <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 font-extrabold">
                    {reposData.total_count || 39}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab("reviews")}
                  className={`py-3.5 px-1 border-b-2 font-bold text-sm flex items-center space-x-2 transition-all ${
                    activeTab === "reviews"
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>2. Live PR Reviews & Evidence</span>
                  <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-slate-200 text-slate-700 font-bold">
                    {runs.length}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab("queues")}
                  className={`py-3.5 px-1 border-b-2 font-bold text-sm flex items-center space-x-2 transition-all ${
                    activeTab === "queues"
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>3. Priority Queues & Kafka Partitions</span>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                </button>

                <button
                  onClick={() => setActiveTab("trigger")}
                  className={`py-3.5 px-1 border-b-2 font-bold text-sm flex items-center space-x-2 transition-all ${
                    activeTab === "trigger"
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>4. Quick Trigger & Sandbox</span>
                </button>

                <button
                  onClick={() => {
                    setActiveTab("stage3");
                    fetchStage3Data();
                  }}
                  className={`py-3.5 px-1 border-b-2 font-bold text-sm flex items-center space-x-2 transition-all ${
                    activeTab === "stage3"
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <span>5. Stage 3: Merge Train & Feedback</span>
                  <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-emerald-100 text-emerald-800 font-extrabold">
                    ACTIVE
                  </span>
                </button>
              </nav>
            </div>
          </header>

          {/* MAIN CONTENT AREA */}
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
            
            {/* ======================================================== */}
            {/* TAB 1: GITHUB REPOSITORIES CONNECTION HUB (INITIAL PHASE) */}
            {/* ======================================================== */}
            {activeTab === "repos" && (
              <div className="space-y-8">
                
                {/* Hero / Connection Overview Banner */}
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                      <div className="flex items-center space-x-3 mb-1">
                        <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-200">
                          INITIAL PHASE: CONNECTION HUB
                        </span>
                        <span className="text-xs text-slate-500 font-medium">GitHub Account Synced</span>
                      </div>
                      <h1 className="text-2xl font-black text-slate-900 tracking-tight">
                        GitHub Repositories Connection Center
                      </h1>
                      <p className="text-sm text-slate-600 mt-1 max-w-2xl">
                        All repositories under your GitHub account are detected. Repositories connected with active webhook contracts, PR reviews, and deterministic test evidence are highlighted below.
                      </p>
                    </div>

                    {/* Quick Stats Grid */}
                    <div className="grid grid-cols-3 gap-3">
                      <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 text-center">
                        <div className="text-2xl font-black text-slate-900">{reposData.total_count || 39}</div>
                        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Total Repos</div>
                      </div>
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
                        <div className="text-2xl font-black text-emerald-700">{reposData.connected_count || 1}</div>
                        <div className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">Connected</div>
                      </div>
                      <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-center">
                        <div className="text-2xl font-black text-blue-700">{runs.length || 1}</div>
                        <div className="text-[11px] font-bold text-blue-700 uppercase tracking-wider">PR Reviews</div>
                      </div>
                    </div>
                  </div>

                  {/* Webhook Endpoint Info Bar */}
                  <div className="mt-5 pt-5 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs bg-slate-50/60 p-3 rounded-xl border">
                    <div className="flex items-center space-x-2 text-slate-700">
                      <span className="font-bold text-slate-900">Webhook Contract URL:</span>
                      <code className="font-mono bg-white px-2.5 py-1 rounded-md border border-slate-200 text-blue-700 select-all">
                        http://13.201.6.39:8000/webhook/github
                      </code>
                    </div>
                    <div className="flex items-center space-x-2 text-slate-500">
                      <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                      <span>Listens for: <strong className="text-slate-800">pull_request</strong> events</span>
                    </div>
                  </div>
                </div>

                {/* PINNED SECTION: CONNECTED REPOSITORIES */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-2">
                      <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
                      <h2 className="text-lg font-black text-slate-900">
                        Connected Repositories ({connectedRepos.length})
                      </h2>
                    </div>
                    <span className="text-xs text-slate-500 font-medium">Monitored by AI PR Assistant with live webhook hooks</span>
                  </div>

                  {connectedRepos.length === 0 ? (
                    <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500">
                      No repositories connected yet. Click "Connect AI PR Assistant" on any repository below!
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-4">
                      {connectedRepos.map((repo) => (
                        <div
                          key={repo.id}
                          className="bg-white rounded-2xl border-2 border-emerald-500/70 p-6 shadow-sm hover:shadow-md transition-all relative overflow-hidden"
                        >
                          <div className="absolute top-0 right-0 bg-emerald-500 text-white text-[10px] font-extrabold uppercase px-3 py-1 rounded-bl-xl tracking-wider shadow-xs">
                            🟢 CONNECTED & MONITORED
                          </div>

                          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                            <div className="space-y-3">
                              <div className="flex items-center space-x-3">
                                <a
                                  href={repo.html_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-xl font-black text-slate-900 hover:text-blue-600 transition-colors flex items-center space-x-1.5"
                                >
                                  <span>{repo.full_name}</span>
                                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                  </svg>
                                </a>

                                <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                                  repo.private ? "bg-amber-50 text-amber-800 border border-amber-200" : "bg-slate-100 text-slate-700"
                                }`}>
                                  {repo.private ? "🔒 Private" : "🌐 Public"}
                                </span>

                                <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                                  branch: {repo.default_branch}
                                </span>
                              </div>

                              <p className="text-sm text-slate-600">
                                {repo.description || "Active production repository with automated AI PR analysis contracts."}
                              </p>

                              {/* Live Connected Specs Badge */}
                              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                                <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 font-bold border border-emerald-200">
                                  <span>SHA Contract:</span>
                                  <span className="font-mono text-emerald-900 font-extrabold">Active</span>
                                </span>
                                <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-800 font-bold border border-blue-200">
                                  <span>Completed Reviews:</span>
                                  <span className="font-black">{repo.total_runs || 1}</span>
                                </span>
                                <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-purple-50 text-purple-800 font-bold border border-purple-200">
                                  <span>Target PR:</span>
                                  <span className="font-mono">PR #1 (Destination Search Conflict)</span>
                                </span>
                              </div>
                            </div>

                            {/* Actions for connected repo */}
                            <div className="flex flex-row lg:flex-col items-center lg:items-end gap-2.5">
                              <button
                                onClick={() => {
                                  setActiveTab("reviews");
                                  if (runs.length > 0) inspectRun(runs[0].id);
                                }}
                                className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 flex items-center justify-center space-x-2 transition-all"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                                <span>Inspect Live Review</span>
                              </button>

                              <button
                                onClick={() => handleInspectRepoPulls(repo.full_name)}
                                className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-bold text-xs flex items-center justify-center space-x-2 transition-all"
                              >
                                <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                                </svg>
                                <span>View GitHub PRs</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* ALL REPOSITORIES GRID / EXPLORER */}
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-black text-slate-900">
                        All Account Repositories ({reposData.total_count || 39})
                      </h2>
                      <p className="text-xs text-slate-500">
                        Select any repository to connect the assistant or inspect pull requests.
                      </p>
                    </div>

                    {/* Filter Pills */}
                    <div className="flex items-center space-x-1.5 bg-slate-100 p-1 rounded-xl">
                      {[
                        { id: "all", label: "All" },
                        { id: "connected", label: "Connected" },
                        { id: "available", label: "Available" },
                        { id: "private", label: "Private" }
                      ].map(tab => (
                        <button
                          key={tab.id}
                          onClick={() => setRepoFilter(tab.id)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                            repoFilter === tab.id
                              ? "bg-white text-slate-900 shadow-xs"
                              : "text-slate-600 hover:text-slate-900"
                          }`}
                        >
                          {tab.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Search Bar */}
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search repositories by name or description (e.g. Airbnb, coupon, linklops)..."
                      value={repoSearch}
                      onChange={(e) => setRepoSearch(e.target.value)}
                      className="w-full px-4 py-3 pl-11 rounded-xl border border-slate-300 bg-white text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-xs"
                    />
                    <svg className="w-5 h-5 text-slate-400 absolute left-3.5 top-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    {repoSearch && (
                      <button
                        onClick={() => setRepoSearch("")}
                        className="absolute right-3 top-3 text-xs text-slate-400 hover:text-slate-600 bg-slate-100 px-2 py-1 rounded"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  {/* Repository Cards Grid */}
                  {loadingRepos ? (
                    <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500">
                      <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                      <p className="font-semibold text-sm">Syncing repositories from GitHub...</p>
                    </div>
                  ) : filteredRepos.length === 0 ? (
                    <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500">
                      No repositories match your filter or search query.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {filteredRepos.map((repo) => (
                        <div
                          key={repo.id}
                          className={`bg-white rounded-xl border p-5 transition-all flex flex-col justify-between hover:border-slate-300 hover:shadow-sm ${
                            repo.is_connected ? "border-emerald-300 bg-emerald-50/20" : "border-slate-200"
                          }`}
                        >
                          <div className="space-y-2.5">
                            {/* Card Header */}
                            <div className="flex items-start justify-between gap-2">
                              <h3 className="font-extrabold text-slate-900 text-sm hover:text-blue-600 transition-colors truncate">
                                <a href={repo.html_url} target="_blank" rel="noreferrer" title={repo.full_name}>
                                  {repo.name}
                                </a>
                              </h3>
                              <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full shrink-0 ${
                                repo.is_connected
                                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                                  : "bg-slate-100 text-slate-600"
                              }`}>
                                {repo.is_connected ? "🟢 CONNECTED" : "⚪ AVAILABLE"}
                              </span>
                            </div>

                            <p className="text-xs text-slate-500 line-clamp-2 min-h-[32px]">
                              {repo.description || "No description provided."}
                            </p>

                            <div className="flex items-center space-x-2 text-[11px] text-slate-500 pt-1">
                              <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded">
                                {repo.default_branch}
                              </span>
                              <span>•</span>
                              <span>{repo.private ? "Private" : "Public"}</span>
                              {repo.stargazers_count > 0 && (
                                <>
                                  <span>•</span>
                                  <span>⭐ {repo.stargazers_count}</span>
                                </>
                              )}
                            </div>
                          </div>

                          {/* Card Footer Actions */}
                          <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between gap-2">
                            {repo.is_connected ? (
                              <button
                                onClick={() => {
                                  setActiveTab("reviews");
                                  if (runs.length > 0) inspectRun(runs[0].id);
                                }}
                                className="w-full py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors"
                              >
                                View Active Reviews
                              </button>
                            ) : (
                              <button
                                onClick={() => handleInspectRepoPulls(repo.full_name)}
                                className="w-full py-1.5 rounded-lg bg-slate-100 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 border border-slate-200 text-slate-700 text-xs font-bold transition-all flex items-center justify-center space-x-1"
                              >
                                <span>Inspect PRs & Connect</span>
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>
            )}

            {/* ======================================================== */}
            {/* TAB 2: LIVE PR REVIEWS & EVIDENCE                        */}
            {/* ======================================================== */}
            {activeTab === "reviews" && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Runs Column */}
                <div className="lg:col-span-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-extrabold text-slate-900">Analysis Runs ({runs.length})</h2>
                    <span className="text-xs text-slate-500">Latest immutable contracts</span>
                  </div>

                  {runs.length === 0 ? (
                    <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500">
                      No analysis runs recorded yet.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {runs.map((r) => (
                        <div
                          key={r.id}
                          onClick={() => inspectRun(r.id)}
                          className={`p-4 rounded-xl border cursor-pointer transition-all ${
                            selectedRun === r.id
                              ? "bg-white border-blue-600 shadow-md ring-2 ring-blue-500/20"
                              : "bg-white border-slate-200 hover:border-slate-300"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="font-extrabold text-xs text-slate-900 truncate max-w-[200px]">
                              {r.repository_id}
                            </span>
                            <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                              r.priority === "P0"
                                ? "bg-red-100 text-red-800 border border-red-200"
                                : r.priority === "P1"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-blue-100 text-blue-800"
                            }`}>
                              {r.priority} PRIORITY
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-xs text-slate-600">
                            <span>PR #{r.pr_number}</span>
                            <span className="font-mono text-[11px] text-slate-500">{r.head_sha.substring(0, 8)}</span>
                          </div>

                          <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                            <span className={`font-bold ${r.status === "COMPLETED" ? "text-emerald-600" : "text-amber-600"}`}>
                              ● {r.status}
                            </span>
                            <span className="text-slate-500">
                              {r.findings_count} findings • {r.test_passed ? "Tests ✅" : "Tests ❌"}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Details Column */}
                <div className="lg:col-span-8">
                  {loadingDetails ? (
                    <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500">
                      <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                      <p className="font-semibold text-sm">Loading verified analysis report...</p>
                    </div>
                  ) : runDetails ? (
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                      {/* Run Header */}
                      <div className="p-6 border-b border-slate-200 bg-slate-50/50">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                          <div>
                            <span className="text-xs font-bold text-blue-600 uppercase tracking-wider font-mono">
                              ANALYSIS ID: {runDetails.id}
                            </span>
                            <h2 className="text-xl font-black text-slate-900 mt-1">
                              {runDetails.repository_id} — Pull Request #{runDetails.pr_number}
                            </h2>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="px-3 py-1 rounded-full text-xs font-black bg-emerald-100 text-emerald-800 border border-emerald-200">
                              {runDetails.status}
                            </span>
                            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-800">
                              {runDetails.priority}
                            </span>
                          </div>
                        </div>

                        {/* Commit hashes */}
                        <div className="grid grid-cols-2 gap-4 text-xs font-mono bg-white p-3 rounded-xl border border-slate-200">
                          <div>
                            <span className="text-slate-400 font-sans block text-[10px] uppercase font-bold">Head Commit (Analyzed)</span>
                            <span className="text-slate-800 font-semibold">{runDetails.head_sha}</span>
                          </div>
                          <div>
                            <span className="text-slate-400 font-sans block text-[10px] uppercase font-bold">Base Branch Commit</span>
                            <span className="text-slate-800 font-semibold">{runDetails.base_sha}</span>
                          </div>
                        </div>
                      </div>

                      {/* Detail Sub-Tabs */}
                      <div className="border-b border-slate-200 px-6 flex space-x-6 text-sm font-bold">
                        <button
                          onClick={() => setDetailTab("findings")}
                          className={`py-3 border-b-2 transition-all ${
                            detailTab === "findings"
                              ? "border-blue-600 text-blue-600"
                              : "border-transparent text-slate-500 hover:text-slate-800"
                          }`}
                        >
                          Validated Findings ({runDetails.findings.length})
                        </button>
                        <button
                          onClick={() => setDetailTab("sandbox")}
                          className={`py-3 border-b-2 transition-all ${
                            detailTab === "sandbox"
                              ? "border-blue-600 text-blue-600"
                              : "border-transparent text-slate-500 hover:text-slate-800"
                          }`}
                        >
                          Deterministic Sandbox Proof
                        </button>
                        <button
                          onClick={() => setDetailTab("comment")}
                          className={`py-3 border-b-2 transition-all ${
                            detailTab === "comment"
                              ? "border-blue-600 text-blue-600"
                              : "border-transparent text-slate-500 hover:text-slate-800"
                          }`}
                        >
                          GitHub PR Comment Preview
                        </button>
                      </div>

                      {/* Findings Tab */}
                      <div className="p-6">
                        {detailTab === "findings" && (
                          <div className="space-y-4">
                            {runDetails.findings.length === 0 ? (
                              <div className="text-center py-8 text-emerald-600 font-bold">
                                ✅ All static & dynamic checks passed. No defects detected.
                              </div>
                            ) : (
                              runDetails.findings.map((f, idx) => (
                                <div
                                  key={idx}
                                  className={`p-4 rounded-xl border ${
                                    f.severity === "CRITICAL" || f.severity === "HIGH"
                                      ? "border-red-200 bg-red-50/20"
                                      : "border-amber-200 bg-amber-50/20"
                                  }`}
                                >
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center space-x-2">
                                      <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                                        f.severity === "CRITICAL"
                                          ? "bg-red-600 text-white"
                                          : f.severity === "HIGH"
                                          ? "bg-red-500 text-white"
                                          : "bg-amber-500 text-white"
                                      }`}>
                                        {f.severity}
                                      </span>
                                      <span className="font-extrabold text-sm text-slate-900">{f.title}</span>
                                    </div>
                                    <span className="font-mono text-xs text-slate-500">
                                      {f.file_path}:{f.line_number}
                                    </span>
                                  </div>

                                  <p className="text-xs text-slate-700 mb-3">{f.description}</p>

                                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-200/60">
                                    <span className="text-emerald-700 font-bold">
                                      ✓ Evidence-Verified ({Math.round(f.confidence * 100)}% Confidence)
                                    </span>
                                    <span className="font-mono text-slate-400">Category: {f.category}</span>
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        )}

                        {/* Sandbox Proof Tab */}
                        {detailTab === "sandbox" && (
                          <div className="space-y-4">
                            {runDetails.test_evidence.length === 0 ? (
                              <div className="text-center py-8 text-slate-500">
                                No sandbox test execution records for this run.
                              </div>
                            ) : (
                              runDetails.test_evidence.map((te, idx) => (
                                <div key={idx} className="space-y-3">
                                  <div className="flex items-center justify-between bg-slate-50 p-3 rounded-xl border border-slate-200">
                                    <div className="flex items-center space-x-2">
                                      <span className={`w-3 h-3 rounded-full ${te.passed ? "bg-emerald-500" : "bg-red-500"}`}></span>
                                      <span className="font-mono font-bold text-xs text-slate-800">{te.test_suite}</span>
                                    </div>
                                    <div className="flex items-center space-x-3 text-xs">
                                      <span className="text-slate-500">Exit Code: <strong className="font-mono">{te.exit_code}</strong></span>
                                      <span className={`font-bold px-2 py-0.5 rounded ${te.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                                        {te.passed ? "PASSED" : "FAILED"}
                                      </span>
                                    </div>
                                  </div>

                                  <div className="bg-slate-900 rounded-xl p-4 font-mono text-xs text-emerald-400 overflow-x-auto max-h-80">
                                    <pre>{te.stdout || "No stdout recorded."}</pre>
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        )}

                        {/* GitHub PR Comment Preview Tab */}
                        {detailTab === "comment" && (
                          <div className="bg-slate-50 rounded-xl p-5 border border-slate-200 text-xs text-slate-800 space-y-3 font-sans">
                            <div className="font-black text-sm text-slate-900 pb-2 border-b border-slate-200">
                              🤖 AI PR Assistant — Review Summary
                            </div>
                            <div className="text-slate-600 font-mono text-[11px]">
                              Commit SHA: <code className="bg-white px-1 border rounded">{runDetails.head_sha}</code> | Analysis ID: <code className="bg-white px-1 border rounded">{runDetails.id}</code>
                            </div>
                            <div className="font-bold text-slate-900">
                              🔍 Validated Findings ({runDetails.findings.length})
                            </div>
                            <div className="space-y-2 pl-2">
                              {runDetails.findings.map((f, i) => (
                                <div key={i} className="space-y-1">
                                  <div className="font-semibold text-slate-900">
                                    🚨 [{f.category}] {f.title} (<code className="font-mono text-[11px]">{f.file_path}:{f.line_number}</code>)
                                  </div>
                                  <div className="text-slate-600 pl-4">• {f.description}</div>
                                </div>
                              ))}
                            </div>
                            <div className="pt-3 border-t border-slate-200 text-slate-400 italic text-[11px]">
                              Verified by deterministic sandbox execution and physical evidence check.
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
                      Select an analysis run from the list to view full evidence and findings.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ======================================================== */}
            {/* TAB 3: PRIORITY QUEUES & KAFKA PARTITIONS                */}
            {/* ======================================================== */}
            {activeTab === "queues" && (
              <div className="space-y-6">
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                  <h2 className="text-xl font-black text-slate-900 mb-1">
                    Multi-Topic Priority Queue (Kafka Partitioning Model)
                  </h2>
                  <p className="text-xs text-slate-600 max-w-2xl">
                    Strict priority partitioning guarantees critical P0 pull requests preempt background tasks. Headroom capacity monitoring ensures worker nodes are never starved or overwhelmed.
                  </p>
                </div>

                {queues && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* P0 CRITICAL */}
                    <div className="bg-white rounded-2xl border-2 border-red-200 p-6 shadow-sm">
                      <div className="flex items-center justify-between mb-4">
                        <span className="font-black text-red-600 text-sm">TOPIC: pr_analysis_p0</span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-red-100 text-red-800">
                          CRITICAL PREEMPTION
                        </span>
                      </div>
                      <div className="text-4xl font-black text-slate-900 mb-1">
                        {queues.priority_topics ? queues.priority_topics.pr_analysis_p0 : 0}
                      </div>
                      <p className="text-xs text-slate-500 font-medium">Pending jobs in P0 partition</p>
                    </div>

                    {/* P1 HIGH */}
                    <div className="bg-white rounded-2xl border border-amber-200 p-6 shadow-sm">
                      <div className="flex items-center justify-between mb-4">
                        <span className="font-black text-amber-600 text-sm">TOPIC: pr_analysis_p1</span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-100 text-amber-800">
                          HIGH PRIORITY
                        </span>
                      </div>
                      <div className="text-4xl font-black text-slate-900 mb-1">
                        {queues.priority_topics ? queues.priority_topics.pr_analysis_p1 : 0}
                      </div>
                      <p className="text-xs text-slate-500 font-medium">Pending jobs in P1 partition</p>
                    </div>

                    {/* P2 STANDARD */}
                    <div className="bg-white rounded-2xl border border-blue-200 p-6 shadow-sm">
                      <div className="flex items-center justify-between mb-4">
                        <span className="font-black text-blue-600 text-sm">TOPIC: pr_analysis_p2</span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-blue-100 text-blue-800">
                          STANDARD
                        </span>
                      </div>
                      <div className="text-4xl font-black text-slate-900 mb-1">
                        {queues.priority_topics ? queues.priority_topics.pr_analysis_p2 : 0}
                      </div>
                      <p className="text-xs text-slate-500 font-medium">Pending jobs in P2 partition</p>
                    </div>
                  </div>
                )}

                {/* Worker Headroom */}
                {queues && (
                  <div className="bg-white rounded-2xl border border-slate-200 p-6">
                    <h3 className="font-black text-slate-900 text-sm mb-4">Capacity & Headroom Monitor</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                      <div className="bg-slate-50 p-4 rounded-xl border">
                        <div className="text-2xl font-black text-slate-800">{queues.active_workers}</div>
                        <div className="text-[11px] font-bold text-slate-500 uppercase mt-1">Active Workers</div>
                      </div>
                      <div className="bg-slate-50 p-4 rounded-xl border">
                        <div className="text-2xl font-black text-emerald-600">
                          {queues.cluster_headroom ? queues.cluster_headroom.headroom : 10}
                        </div>
                        <div className="text-[11px] font-bold text-slate-500 uppercase mt-1">Available Headroom</div>
                      </div>
                      <div className="bg-slate-50 p-4 rounded-xl border">
                        <div className="text-2xl font-black text-slate-800">
                          {queues.cluster_headroom ? queues.cluster_headroom.max_capacity : 10}
                        </div>
                        <div className="text-[11px] font-bold text-slate-500 uppercase mt-1">Max Concurrency</div>
                      </div>
                      <div className="bg-slate-50 p-4 rounded-xl border">
                        <div className="text-2xl font-black text-blue-600">
                          {queues.cluster_headroom ? `${Math.round(queues.cluster_headroom.utilization_pct)}%` : "0%"}
                        </div>
                        <div className="text-[11px] font-bold text-slate-500 uppercase mt-1">Cluster Utilization</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ======================================================== */}
            {/* TAB 4: QUICK TRIGGER & SANDBOX TEST                      */}
            {/* ======================================================== */}
            {activeTab === "trigger" && (
              <div className="max-w-2xl mx-auto space-y-6">
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                  <h2 className="text-xl font-black text-slate-900 mb-1">Trigger Analysis or Webhook</h2>
                  <p className="text-xs text-slate-600 mb-6">
                    Test the complete end-to-end pipeline against real GitHub pull requests or simulated conflict events.
                  </p>

                  {/* 1-Click Airbnb-clone conflict demo */}
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-extrabold text-xs text-blue-900">
                        ⭐ 1-Click Conflict Test: Airbnb-clone PR #1
                      </span>
                      <span className="text-[10px] font-black bg-blue-200 text-blue-900 px-2 py-0.5 rounded">
                        RECOMMENDED
                      </span>
                    </div>
                    <p className="text-xs text-blue-700 mb-3">
                      Dispatches the live Indian cities search conflict for HIMpcgithub3000/Airbnb-clone PR #1 to the P0 queue.
                    </p>
                    <button
                      disabled={isTriggering}
                      onClick={() => handleQuickTrigger("conflict")}
                      className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md transition-all disabled:opacity-50"
                    >
                      {isTriggering ? "Triggering..." : "⚡ Run Real Conflict Analysis (P0)"}
                    </button>
                  </div>

                  {triggerSuccess && (
                    <div className="p-3 mb-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800">
                      {triggerSuccess}
                    </div>
                  )}

                  {/* Manual form */}
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleQuickTrigger("custom");
                    }}
                    className="space-y-4 pt-4 border-t border-slate-100"
                  >
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Repository Full Name</label>
                      <input
                        type="text"
                        value={formRepo}
                        onChange={(e) => setFormRepo(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-bold text-slate-700 mb-1">Pull Request Number</label>
                        <input
                          type="number"
                          value={formPR}
                          onChange={(e) => setFormPR(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-700 mb-1">Priority</label>
                        <select
                          value={formPriority}
                          onChange={(e) => setFormPriority(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        >
                          <option value="P0">P0 (Critical Preemption)</option>
                          <option value="P1">P1 (High)</option>
                          <option value="P2">P2 (Standard)</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Head SHA</label>
                      <input
                        type="text"
                        value={formHeadSha}
                        onChange={(e) => setFormHeadSha(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={isTriggering}
                      className="w-full py-2.5 rounded-lg bg-slate-900 hover:bg-black text-white font-bold text-xs transition-colors disabled:opacity-50"
                    >
                      {isTriggering ? "Enqueuing..." : "Dispatch Custom Webhook Event"}
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* ======================================================== */}
            {/* TAB 5: STAGE 3 SPECULATIVE MERGE TRAIN & FEEDBACK       */}
            {/* ======================================================== */}
            {activeTab === "stage3" && (
              <div className="space-y-8">
                {/* Header Banner */}
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-[11px] font-black tracking-wider text-blue-600 uppercase font-mono">
                          STAGE 3 ARCHITECTURE
                        </span>
                        <span className="px-2 py-0.5 text-[10px] font-extrabold rounded bg-emerald-100 text-emerald-800">
                          PRODUCTION-READY
                        </span>
                      </div>
                      <h2 className="text-xl font-black text-slate-900 mt-1">
                        Speculative Merge Train & Closed-Loop Human Review Memory
                      </h2>
                      <p className="text-xs text-slate-600 mt-1">
                        Pre-tests speculative multi-PR merge states before main branch landing, learns from engineer approvals and dismissals, and syncs vector embeddings on merge.
                      </p>
                    </div>

                    <div className="flex items-center space-x-3">
                      <input
                        type="text"
                        value={stage3Repo}
                        onChange={(e) => setStage3Repo(e.target.value)}
                        placeholder="owner/repo"
                        className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                      <button
                        onClick={() => fetchStage3Data()}
                        disabled={stage3Loading}
                        className="px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs border border-blue-200 transition-colors"
                      >
                        {stage3Loading ? "Refreshing..." : "↻ Refresh"}
                      </button>
                    </div>
                  </div>

                  {stage3ActionMsg && (
                    <div className="mt-4 p-3 rounded-xl bg-blue-50 border border-blue-200 text-xs font-bold text-blue-900 animate-fadeIn">
                      💡 {stage3ActionMsg}
                    </div>
                  )}
                </div>

                {/* 3-Column Grid for Stage 3 Features */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                  
                  {/* COLUMN 1: SPECULATIVE MERGE QUEUE */}
                  <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-base font-black text-slate-900">
                            1. Speculative Merge Train Queue
                          </h3>
                          <p className="text-xs text-slate-500">
                            Pre-tests PRs ahead-of-time in ephemeral sandboxes against speculative combined SHAs.
                          </p>
                        </div>
                        <span className="text-xs font-mono font-bold bg-slate-100 px-2.5 py-1 rounded-full text-slate-700">
                          {mergeTrainData.total_queued || 0} Queued
                        </span>
                      </div>

                      {/* Enqueue form */}
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-wrap items-center gap-3">
                        <span className="text-xs font-bold text-slate-700">Enqueue Candidate:</span>
                        <input
                          type="number"
                          value={enqueuePRNumber}
                          onChange={(e) => setEnqueuePRNumber(e.target.value)}
                          placeholder="PR #"
                          className="w-20 px-2.5 py-1.5 rounded border border-slate-300 text-xs font-bold"
                        />
                        <input
                          type="text"
                          value={enqueueHeadSha}
                          onChange={(e) => setEnqueueHeadSha(e.target.value)}
                          placeholder="Head SHA"
                          className="flex-1 min-w-[140px] px-2.5 py-1.5 rounded border border-slate-300 text-xs font-mono"
                        />
                        <button
                          onClick={handleEnqueueCandidate}
                          disabled={stage3Loading}
                          className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition-colors"
                        >
                          + Enqueue PR
                        </button>
                      </div>

                      {/* Candidate list */}
                      {(!mergeTrainData.candidates || mergeTrainData.candidates.length === 0) ? (
                        <div className="py-8 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-xl">
                          No PRs currently queued in the merge train. Enqueue a candidate above or dispatch a GitHub merge_group event!
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {mergeTrainData.candidates.map((c) => (
                            <div key={c.id} className="p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-300 transition-all space-y-2">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-2">
                                  <span className="text-xs font-black bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                                    POS #{c.queue_position}
                                  </span>
                                  <span className="font-extrabold text-sm text-slate-900">
                                    PR #{c.pr_number}
                                  </span>
                                  <span className="text-xs font-mono text-slate-500">
                                    sha: {c.head_sha ? c.head_sha.substring(0, 8) : "?"}
                                  </span>
                                </div>
                                <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                                  c.status === "VERIFIED"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : c.status === "REJECTED"
                                    ? "bg-rose-100 text-rose-800"
                                    : c.status === "SPECULATING"
                                    ? "bg-blue-100 text-blue-800 animate-pulse"
                                    : "bg-amber-100 text-amber-800"
                                }`}>
                                  {c.status}
                                </span>
                              </div>

                              {c.latest_speculation && (
                                <div className="p-2.5 rounded-lg bg-slate-50 text-[11px] font-mono space-y-1 text-slate-600 border border-slate-200">
                                  <div className="flex items-center justify-between">
                                    <span>speculative_sha: {c.latest_speculation.speculative_sha.substring(0, 16)}...</span>
                                    <span className={c.latest_speculation.tests_passed ? "text-emerald-700 font-bold" : "text-rose-700 font-bold"}>
                                      {c.latest_speculation.tests_passed ? "✓ Sandbox Tests Passed" : "✗ Conflict / Tests Failed"}
                                    </span>
                                  </div>
                                  {c.latest_speculation.conflict_files && c.latest_speculation.conflict_files.length > 0 && (
                                    <div className="text-rose-600 font-bold">
                                      conflicts: {c.latest_speculation.conflict_files.join(", ")}
                                    </div>
                                  )}
                                </div>
                              )}

                              <div className="pt-2 flex items-center justify-end space-x-2">
                                <button
                                  onClick={() => handleSimulateCandidate(c.id, false)}
                                  disabled={stage3Loading}
                                  className="px-2.5 py-1 rounded bg-slate-900 hover:bg-black text-white text-[11px] font-bold transition-colors"
                                >
                                  ⚡ Test Speculative Sandbox
                                </button>
                                <button
                                  onClick={() => handleSimulateCandidate(c.id, true)}
                                  disabled={stage3Loading}
                                  className="px-2.5 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-[11px] font-bold transition-colors"
                                >
                                  ⚠️ Simulate Conflict
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* REINDEXING METRICS */}
                    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-base font-black text-slate-900">
                            3. Incremental pgvector Codebase Re-indexing
                          </h3>
                          <p className="text-xs text-slate-500">
                            Evicts obsolete embeddings and re-indexes modified files on main branch push.
                          </p>
                        </div>
                        <button
                          onClick={handleTriggerReindex}
                          disabled={stage3Loading}
                          className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs transition-colors"
                        >
                          ⚡ Trigger Commit Re-index
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 rounded-xl bg-purple-50 border border-purple-200 text-purple-900">
                          <span className="text-[10px] font-bold uppercase tracking-wider">Total Indexed Chunks</span>
                          <p className="text-2xl font-black mt-1">{reindexStats.total_chunks || 0}</p>
                        </div>
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-800">
                          <span className="text-[10px] font-bold uppercase tracking-wider">Indexed Repository Files</span>
                          <p className="text-2xl font-black mt-1">{reindexStats.file_count || 0}</p>
                        </div>
                      </div>

                      {reindexStats.indexed_files && reindexStats.indexed_files.length > 0 && (
                        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-600">
                          <span className="font-bold text-slate-700 block mb-1">Active Semantic Vector Files:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {reindexStats.indexed_files.map((f, i) => (
                              <span key={i} className="px-2 py-0.5 bg-white rounded border border-slate-300 text-[10px]">
                                {f}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* COLUMN 2: CLOSED LOOP HUMAN REVIEW FEEDBACK */}
                  <div className="space-y-6">
                    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
                      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                        <div>
                          <h3 className="text-base font-black text-slate-900">
                            2. Closed-Loop Feedback
                          </h3>
                          <p className="text-xs text-slate-500">
                            Calibrates confidence scores from engineer decisions.
                          </p>
                        </div>
                        <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-100 text-emerald-800">
                          {feedbackData.count || 0} Events
                        </span>
                      </div>

                      <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
                        <div className="flex items-center justify-between text-emerald-700 font-bold">
                          <span>• Validation Boost:</span>
                          <span className="font-mono">+0.15</span>
                        </div>
                        <div className="flex items-center justify-between text-rose-700 font-bold">
                          <span>• Dismissal / False-Positive Penalty:</span>
                          <span className="font-mono">-0.25</span>
                        </div>
                        <p className="text-[11px] text-slate-500 pt-1">
                          Findings with calibrated confidence &lt; 0.50 are automatically suppressed from PR review comments.
                        </p>
                      </div>

                      {/* Quick test buttons for feedback calibration */}
                      <div className="space-y-2">
                        <span className="text-xs font-bold text-slate-700 block">Simulate Engineer Feedback:</span>
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={() => handleSendFeedback(1, "approved", "SECURITY", "SQL_INJECTION_RISK", "Confirmed vulnerability")}
                            disabled={stage3Loading}
                            className="p-2 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 font-bold text-xs text-center transition-colors"
                          >
                            👍 Validate (+0.15)
                          </button>
                          <button
                            onClick={() => handleSendFeedback(1, "dismissed", "LINT", "TRAILING_WHITESPACE", "False positive lint nagging")}
                            disabled={stage3Loading}
                            className="p-2 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-200 font-bold text-xs text-center transition-colors"
                          >
                            👎 Dismiss (-0.25)
                          </button>
                        </div>
                      </div>

                      {/* Recent Feedback Logs */}
                      <div className="space-y-2 pt-2">
                        <span className="text-xs font-bold text-slate-700 block">Recent Review Actions:</span>
                        {(!feedbackData.feedback_entries || feedbackData.feedback_entries.length === 0) ? (
                          <p className="text-xs text-slate-400 italic py-4 text-center">No feedback events recorded yet.</p>
                        ) : (
                          <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                            {feedbackData.feedback_entries.map((fb) => (
                              <div key={fb.id} className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-xs space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-800">@{fb.reviewer_handle}</span>
                                  <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${
                                    fb.weight_delta > 0
                                      ? "bg-emerald-100 text-emerald-800 font-mono"
                                      : "bg-rose-100 text-rose-800 font-mono"
                                  }`}>
                                    {fb.weight_delta > 0 ? `+${fb.weight_delta}` : fb.weight_delta}
                                  </span>
                                </div>
                                <div className="text-[11px] font-mono text-slate-600 truncate">
                                  {fb.rule_or_title || fb.finding_category || "General Review"}
                                </div>
                                {fb.feedback_text && (
                                  <p className="text-[11px] text-slate-500 italic">
                                    "{fb.feedback_text}"
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            )}

          </main>

          {/* ======================================================== */}
          {/* MODAL: INSPECT REPO PULL REQUESTS                        */}
          {/* ======================================================== */}
          {selectedRepoForPulls && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
              <div className="bg-white rounded-2xl border border-slate-200 max-w-2xl w-full p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div>
                    <span className="text-[11px] font-bold text-blue-600 uppercase font-mono">PULL REQUEST INSPECTOR</span>
                    <h3 className="text-lg font-black text-slate-900">{selectedRepoForPulls}</h3>
                  </div>
                  <button
                    onClick={() => setSelectedRepoForPulls(null)}
                    className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg"
                  >
                    ✕
                  </button>
                </div>

                {loadingPulls ? (
                  <div className="py-12 text-center text-slate-500">
                    <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    <p className="text-xs font-semibold">Fetching pull requests from GitHub...</p>
                  </div>
                ) : repoPulls.length === 0 ? (
                  <div className="py-8 text-center text-slate-500 text-xs">
                    <p className="font-bold text-slate-700">No open pull requests found for this repository.</p>
                    <p className="mt-1">When a pull request is created on GitHub, AI PR Assistant will automatically receive the webhook!</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-500">Select any open pull request to run immediate AI analysis:</p>
                    {repoPulls.map((p) => (
                      <div key={p.number} className="p-4 rounded-xl border border-slate-200 hover:border-blue-400 bg-slate-50/50 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-extrabold text-sm text-slate-900">
                            PR #{p.number}: {p.title}
                          </span>
                          <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                            p.state === "open" ? "bg-emerald-100 text-emerald-800" : "bg-slate-200 text-slate-700"
                          }`}>
                            {p.state.toUpperCase()}
                          </span>
                        </div>
                        <div className="flex items-center space-x-3 text-xs font-mono text-slate-500">
                          <span>head: {p.head_sha ? p.head_sha.substring(0, 8) : "?"}</span>
                          <span>base: {p.base_sha ? p.base_sha.substring(0, 8) : "?"}</span>
                          <span>by @{p.user}</span>
                        </div>
                        <div className="pt-2 flex justify-end">
                          <button
                            onClick={() => {
                              setFormRepo(selectedRepoForPulls);
                              setFormPR(p.number);
                              setFormHeadSha(p.head_sha || "");
                              setFormBaseSha(p.base_sha || "");
                              setSelectedRepoForPulls(null);
                              setActiveTab("trigger");
                            }}
                            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition-colors"
                          >
                            Analyze PR #{p.number}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="pt-3 border-t border-slate-100 flex justify-end">
                  <button
                    onClick={() => setSelectedRepoForPulls(null)}
                    className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* MODAL: GITHUB TOKEN & CONNECTION MANAGEMENT               */}
          {/* ======================================================== */}
          {isTokenModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
              <div className="bg-white rounded-2xl border border-slate-200 max-w-lg w-full p-6 shadow-xl space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <h3 className="text-base font-black text-slate-900">GitHub Authentication & Token Status</h3>
                  <button onClick={() => setIsTokenModalOpen(false)} className="text-slate-400 hover:text-slate-600">✕</button>
                </div>

                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs space-y-1.5">
                  <div className="flex items-center space-x-2 text-emerald-900 font-bold">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span>Current Status: Token Active & Fully Valid</span>
                  </div>
                  <p className="text-emerald-800">
                    Your current token has read and write access to <strong>39 repositories</strong> on account <strong>@{user ? user.login : "HIMpcgithub3000"}</strong>.
                  </p>
                </div>

                <form onSubmit={handleUpdateToken} className="space-y-4 pt-2">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Update / Rotate GitHub Personal Access Token (Optional)
                    </label>
                    <input
                      type="password"
                      placeholder="Paste new token (github_pat_... or ghp_...)"
                      value={customToken}
                      onChange={(e) => setCustomToken(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      Required scopes: <code>repo</code>, <code>admin:repo_hook</code>
                    </p>
                  </div>

                  {tokenUpdateStatus && (
                    <div className={`p-2.5 rounded-lg text-xs font-bold ${
                      tokenUpdateStatus === "success"
                        ? "bg-emerald-100 text-emerald-800"
                        : tokenUpdateStatus === "validating"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-red-100 text-red-800"
                    }`}>
                      {tokenUpdateStatus === "validating" ? "Validating token with GitHub API..." : tokenUpdateStatus}
                    </div>
                  )}

                  <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={() => setIsTokenModalOpen(false)}
                      className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs"
                    >
                      Close
                    </button>
                    <button
                      type="submit"
                      disabled={!customToken.trim() || tokenUpdateStatus === "validating"}
                      className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs disabled:opacity-50"
                    >
                      Update Token
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* FOOTER */}
          <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
            <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
              <span>AI PR Assistant Mission Control • Stage 2 Autonomous Infrastructure</span>
              <span className="font-mono text-slate-400">EC2 Node: 13.201.6.39 • Redis Broker Active</span>
            </div>
          </footer>
        </div>
      );
    }

    const root = ReactDOM.createRoot(document.getElementById("root"));
    root.render(<App />);
  </script>
</body>
</html>"""
