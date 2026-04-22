import { useState } from "react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";

// ── Simulated audit data (replace with API call to your Python backend) ──────
const AUDIT_DATA = {
  org: "Acme Corp",
  runId: "20250421_143022",
  overallMaturity: 58.4,
  generatedAt: "2025-04-21T14:30:22Z",
  frameworks: [
    { id: "nist_ai_rmf", label: "NIST AI RMF", maturity: 51.2, total: 8, compliant: 2, partial: 2, inDev: 1, gaps: 3, critical: 3 },
    { id: "iso_42001",   label: "ISO 42001",   maturity: 55.0, total: 4, compliant: 1, partial: 1, inDev: 1, gaps: 1, critical: 1 },
    { id: "soc2",        label: "SOC 2",       maturity: 66.7, total: 6, compliant: 2, partial: 2, inDev: 1, gaps: 1, critical: 0 },
    { id: "nist_800_53", label: "NIST 800-53", maturity: 60.4, total: 12, compliant: 4, partial: 3, inDev: 2, gaps: 3, critical: 2 },
  ],
  uarFindings: [
    { id: "u003", name: "Carol Smith", severity: "critical", rule: "UAR-001", description: "Terminated user with active system access", systems: ["Okta", "Jira", "Confluence"], action: "Immediately revoke all system access." },
    { id: "u002", name: "Bob Reyes",   severity: "high",     rule: "UAR-002", description: "Contractor with production database access", systems: ["Prod-DB", "AWS"], action: "Apply least-privilege. Add MFA." },
    { id: "u002", name: "Bob Reyes",   severity: "medium",   rule: "UAR-003", description: "Manager review overdue", systems: ["AWS", "GitHub"], action: "Send reminder to manager." },
    { id: "u004", name: "David Park",  severity: "low",      rule: "UAR-004", description: "Dormant account (270 days inactive)", systems: ["AWS", "Slack"], action: "Disable account pending confirmation." },
    { id: "u005", name: "Eva Torres",  severity: "medium",   rule: "UAR-005", description: "No manager review on record", systems: ["GitHub", "Jira"], action: "Initiate manager review." },
  ],
  criticalGaps: [
    { id: "GOVERN-1.1", framework: "NIST AI RMF", description: "AI risk policies and risk tolerance documented", riskScore: 8.7, effort: "High", remediation: "Establish a formal AI risk appetite statement approved by executive leadership, aligned to NIST AI RMF GOVERN-1.1. Document risk tolerance thresholds and review annually." },
    { id: "MEASURE-2.5", framework: "NIST AI RMF", description: "AI system performance monitored post-deployment", riskScore: 8.2, effort: "High", remediation: "Implement a model monitoring pipeline with drift detection and performance degradation alerts. Reference MEASURE-2.5 requirements for post-deployment evaluation cadence." },
    { id: "AC-6", framework: "NIST 800-53", description: "Least privilege not consistently applied", riskScore: 7.9, effort: "Medium", remediation: "Conduct a least-privilege review for all contractor accounts. Remove unnecessary production database access and enforce role-based access controls per AC-6." },
    { id: "GOVERN-1.2", framework: "NIST AI RMF", description: "AI risk management roles and responsibilities assigned", riskScore: 7.4, effort: "Medium", remediation: "Define and document AI governance roles including AI Risk Owner, Model Owner, and Ethics Reviewer. Publish RACI matrix aligned to NIST AI RMF GOVERN-1.2." },
    { id: "RA-5", framework: "NIST 800-53", description: "Vulnerability scanning ad hoc, not on schedule", riskScore: 6.8, effort: "Low", remediation: "Establish a scheduled vulnerability scanning program with monthly scans for critical systems. Integrate findings into the risk register per RA-5 requirements." },
  ],
  recommendations: [
    "Remediate all critical UAR findings within 72 hours, prioritizing terminated user account revocation.",
    "Establish AI governance policy and risk appetite statement aligned to NIST AI RMF GOVERN function.",
    "Implement post-deployment AI model monitoring pipeline per MEASURE-2.5 requirements.",
    "Conduct comprehensive least-privilege review for all contractor and third-party accounts.",
    "Close evidence gaps for all controls scoring below 2, starting with GOVERN-1.1 and AC-6.",
  ],
};

// ── Helpers ───────────────────────────────────────────────────────────────────
const SEVERITY_CONFIG = {
  critical: { color: "#ef4444", bg: "bg-red-950/60",   border: "border-red-800",   label: "CRITICAL" },
  high:     { color: "#f97316", bg: "bg-orange-950/60", border: "border-orange-800", label: "HIGH" },
  medium:   { color: "#eab308", bg: "bg-yellow-950/60", border: "border-yellow-800", label: "MEDIUM" },
  low:      { color: "#3b82f6", bg: "bg-blue-950/60",   border: "border-blue-800",   label: "LOW" },
};

const maturityColor = (score) => {
  if (score >= 75) return "#22c55e";
  if (score >= 50) return "#eab308";
  if (score >= 25) return "#f97316";
  return "#ef4444";
};

const maturityLabel = (score) => {
  if (score >= 75) return "Managed";
  if (score >= 50) return "Developing";
  if (score >= 25) return "Initial";
  return "Incomplete";
};

const riskScoreColor = (score) => {
  if (score >= 8) return "text-red-400";
  if (score >= 6) return "text-orange-400";
  if (score >= 4) return "text-yellow-400";
  return "text-blue-400";
};

// ── Components ────────────────────────────────────────────────────────────────

function MaturityRing({ score, size = 80 }) {
  const r = size * 0.38;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = maturityColor(score);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1e293b" strokeWidth={size*0.08} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={size*0.08}
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        fill={color} fontSize={size*0.22} fontWeight="700" fontFamily="monospace">
        {score.toFixed(0)}
      </text>
    </svg>
  );
}

function SeverityBadge({ severity }) {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.low;
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded border ${cfg.bg} ${cfg.border}`}
      style={{ color: cfg.color, letterSpacing: "0.08em" }}>
      {cfg.label}
    </span>
  );
}

function FrameworkCard({ fw, onClick, selected }) {
  const color = maturityColor(fw.maturity);
  return (
    <button onClick={() => onClick(fw)}
      className={`w-full text-left p-4 rounded-xl border transition-all duration-200 ${
        selected ? "border-cyan-500 bg-cyan-950/30" : "border-slate-700 bg-slate-800/50 hover:border-slate-500"
      }`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-slate-200">{fw.label}</span>
        <MaturityRing score={fw.maturity} size={48} />
      </div>
      <div className="grid grid-cols-4 gap-1 text-center text-xs">
        {[
          { label: "OK", val: fw.compliant, color: "text-green-400" },
          { label: "Part", val: fw.partial, color: "text-yellow-400" },
          { label: "Dev", val: fw.inDev, color: "text-orange-400" },
          { label: "Gap", val: fw.gaps, color: "text-red-400" },
        ].map(({ label, val, color }) => (
          <div key={label}>
            <div className={`font-bold text-base ${color}`}>{val}</div>
            <div className="text-slate-500">{label}</div>
          </div>
        ))}
      </div>
    </button>
  );
}

function UARTable({ findings }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700 text-left text-slate-400 text-xs uppercase tracking-wider">
            <th className="pb-2 pr-4">User</th>
            <th className="pb-2 pr-4">Severity</th>
            <th className="pb-2 pr-4">Finding</th>
            <th className="pb-2 pr-4">Systems</th>
            <th className="pb-2">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {findings.map((f, i) => (
            <tr key={i} className="hover:bg-slate-800/40 transition-colors">
              <td className="py-2.5 pr-4 font-medium text-slate-200 whitespace-nowrap">{f.name}</td>
              <td className="py-2.5 pr-4"><SeverityBadge severity={f.severity} /></td>
              <td className="py-2.5 pr-4 text-slate-400 max-w-xs">{f.description}</td>
              <td className="py-2.5 pr-4">
                <div className="flex flex-wrap gap-1">
                  {f.systems.map(s => (
                    <span key={s} className="text-xs bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded">{s}</span>
                  ))}
                </div>
              </td>
              <td className="py-2.5 text-slate-400 text-xs max-w-xs">{f.action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GapCard({ gap }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border border-slate-700 rounded-xl overflow-hidden hover:border-slate-600 transition-colors">
      <button className="w-full text-left p-4" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs text-cyan-400 font-bold">{gap.id}</span>
              <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded">{gap.framework}</span>
              <span className={`text-xs font-medium ${
                gap.effort === "High" ? "text-red-400" : gap.effort === "Medium" ? "text-yellow-400" : "text-green-400"
              }`}>{gap.effort} effort</span>
            </div>
            <p className="text-sm text-slate-300">{gap.description}</p>
          </div>
          <div className="text-right shrink-0">
            <div className={`text-2xl font-bold font-mono ${riskScoreColor(gap.riskScore)}`}>
              {gap.riskScore.toFixed(1)}
            </div>
            <div className="text-xs text-slate-500">risk score</div>
          </div>
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-800 pt-3">
          <p className="text-xs text-slate-500 mb-1 font-semibold uppercase tracking-wider">AI-Generated Remediation</p>
          <p className="text-sm text-slate-300 leading-relaxed">{gap.remediation}</p>
          <p className="text-xs text-slate-600 mt-2 italic">⚠ Human review required before action.</p>
        </div>
      )}
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function AuditDashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedFw, setSelectedFw] = useState(null);
  const data = AUDIT_DATA;

  const radarData = data.frameworks.map(fw => ({
    subject: fw.label.replace("NIST ", "").replace("ISO ", "ISO\n"),
    score: fw.maturity,
  }));

  const barData = data.criticalGaps.map(g => ({
    name: g.id,
    score: g.riskScore,
    color: g.riskScore >= 8 ? "#ef4444" : g.riskScore >= 6 ? "#f97316" : "#eab308",
  }));

  const tabs = [
    { id: "overview",    label: "Overview" },
    { id: "frameworks",  label: "Frameworks" },
    { id: "uar",         label: `UAR (${data.uarFindings.length})` },
    { id: "gaps",        label: `Gaps (${data.criticalGaps.length})` },
    { id: "recommend",   label: "Recommendations" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100"
      style={{ fontFamily: "'IBM Plex Mono', 'Courier New', monospace" }}>

      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-10 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span className="text-xs text-cyan-400 font-bold tracking-widest uppercase">
                  AI Trust & Audit Agent
                </span>
              </div>
              <h1 className="text-xl font-bold text-white mt-0.5">{data.org}</h1>
            </div>
            <div className="text-right text-xs text-slate-500">
              <div>Run ID: <span className="text-slate-400 font-mono">{data.runId}</span></div>
              <div className="mt-0.5">{new Date(data.generatedAt).toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">

        {/* KPI Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Overall Maturity", value: `${data.overallMaturity.toFixed(1)}`, unit: "/100",
              sub: maturityLabel(data.overallMaturity), color: maturityColor(data.overallMaturity) },
            { label: "Frameworks", value: data.frameworks.length, unit: " assessed",
              sub: data.frameworks.map(f => f.label.split(" ")[0]).join(" · "), color: "#22d3ee" },
            { label: "Critical Findings", value: data.uarFindings.filter(f => f.severity === "critical").length +
              data.criticalGaps.filter(g => g.riskScore >= 8).length,
              sub: "Require immediate action", color: "#ef4444" },
            { label: "Evidence Gaps", value: data.criticalGaps.length,
              unit: " controls", sub: "Below maturity threshold", color: "#f97316" },
          ].map(kpi => (
            <div key={kpi.label} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">{kpi.label}</div>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold font-mono" style={{ color: kpi.color }}>{kpi.value}</span>
                {kpi.unit && <span className="text-slate-500 text-sm">{kpi.unit}</span>}
              </div>
              <div className="text-xs text-slate-600 mt-1">{kpi.sub}</div>
            </div>
          ))}
        </div>

        {/* Tab Nav */}
        <div className="flex gap-1 mb-6 bg-slate-900 border border-slate-800 rounded-xl p-1">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                activeTab === tab.id
                  ? "bg-cyan-500 text-slate-950"
                  : "text-slate-400 hover:text-slate-200"
              }`}>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}

        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Radar */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
                Framework Maturity Radar
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#334155" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <Radar dataKey="score" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.15}
                    strokeWidth={2} dot={{ fill: "#22d3ee", r: 3 }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Risk Bar */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
                Top Risk Scores by Control
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData} layout="vertical" margin={{ left: 16 }}>
                  <XAxis type="number" domain={[0, 10]} tick={{ fill: "#64748b", fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} width={90} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }}
                    labelStyle={{ color: "#e2e8f0" }}
                    itemStyle={{ color: "#22d3ee" }}
                  />
                  <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                    {barData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* UAR Summary */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 lg:col-span-2">
              <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
                UAR Finding Summary
              </h2>
              <div className="grid grid-cols-4 gap-4">
                {["critical", "high", "medium", "low"].map(sev => {
                  const count = data.uarFindings.filter(f => f.severity === sev).length;
                  const cfg = SEVERITY_CONFIG[sev];
                  return (
                    <div key={sev} className={`rounded-xl border p-4 text-center ${cfg.bg} ${cfg.border}`}>
                      <div className="text-3xl font-bold font-mono" style={{ color: cfg.color }}>{count}</div>
                      <div className="text-xs font-bold mt-1" style={{ color: cfg.color }}>{cfg.label}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {activeTab === "frameworks" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {data.frameworks.map(fw => (
              <FrameworkCard key={fw.id} fw={fw}
                onClick={setSelectedFw}
                selected={selectedFw?.id === fw.id} />
            ))}
            {selectedFw && (
              <div className="md:col-span-2 lg:col-span-4 bg-slate-900 border border-cyan-800 rounded-xl p-6">
                <h3 className="text-cyan-400 font-bold mb-4">{selectedFw.label} — Control Distribution</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                  {[
                    { label: "Compliant (4)", val: selectedFw.compliant, color: "text-green-400", desc: "Fully implemented + evidenced" },
                    { label: "Partial (3)", val: selectedFw.partial, color: "text-yellow-400", desc: "Implemented, evidence incomplete" },
                    { label: "In Dev (2)", val: selectedFw.inDev, color: "text-orange-400", desc: "In progress, no evidence" },
                    { label: "Gap (0-1)", val: selectedFw.gaps, color: "text-red-400", desc: "Not addressed or planned only" },
                  ].map(item => (
                    <div key={item.label} className="bg-slate-800 rounded-xl p-4">
                      <div className={`text-4xl font-bold font-mono ${item.color}`}>{item.val}</div>
                      <div className="text-sm font-semibold text-slate-300 mt-1">{item.label}</div>
                      <div className="text-xs text-slate-500 mt-1">{item.desc}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "uar" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">
              User Access Review Findings
            </h2>
            <UARTable findings={data.uarFindings} />
          </div>
        )}

        {activeTab === "gaps" && (
          <div className="space-y-3">
            <p className="text-xs text-slate-500 mb-4">
              Click any finding to expand AI-generated remediation guidance. All recommendations require human review before action.
            </p>
            {data.criticalGaps.map(gap => (
              <GapCard key={gap.id} gap={gap} />
            ))}
          </div>
        )}

        {activeTab === "recommend" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-sm font-semibold text-slate-300 mb-2 uppercase tracking-wider">
              Strategic Recommendations
            </h2>
            <p className="text-xs text-slate-500 mb-6">AI-generated · Human review required before implementation</p>
            <div className="space-y-4">
              {data.recommendations.map((rec, i) => (
                <div key={i} className="flex gap-4 p-4 bg-slate-800/50 border border-slate-700 rounded-xl">
                  <div className="shrink-0 w-8 h-8 rounded-full bg-cyan-950 border border-cyan-800 flex items-center justify-center">
                    <span className="text-cyan-400 font-bold text-sm">{i + 1}</span>
                  </div>
                  <p className="text-sm text-slate-300 leading-relaxed pt-1">{rec}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
