/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Reconciliation.tsx — Token Usage Dashboard
 * Matches FinDoc AI design system (Material You / neutral palette + CSS vars)
 */

import {
    Activity,
    AlertCircle,
    ArrowDownRight,
    ArrowUpRight,
    BarChart2,
    Calendar,
    ChevronDown,
    Clock,
    Download,
    FileText,
    Landmark,
    LayoutDashboard,
    MessageSquare,
    Minus,
    Moon,
    MoreVertical,
    Plus,
    RefreshCw,
    Settings,
    Sparkles,
    Sun,
    TrendingUp,
    Zap,
    LucideIcon,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import React, {
    useState,
    useEffect,
    useCallback,
    useRef,
} from 'react';

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
interface TokenUsageRecord {
    session_id: string;
    timestamp: string;
    model: string;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cost_usd: number;
}

interface UsageSummary {
    period: string;
    period_start: string | null;
    period_end: string | null;
    session_count: number;
    total_input: number;
    total_output: number;
    total_tokens: number;
    total_cost_usd: number;
    records: TokenUsageRecord[];
}

interface NavItem {
    icon: LucideIcon;
    label: string;
    href: string;
    active: boolean;
}

type Period = '24h' | '7d' | '30d' | 'all';

/* ─────────────────────────────────────────────
   Constants
───────────────────────────────────────────── */
const BACKEND_URL = 'http://127.0.0.1:8000';

const NAV_ITEMS: NavItem[] = [
    { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard', active: false },
    { icon: MessageSquare, label: 'Chat Assistant', href: '/chat', active: false },
    { icon: Landmark, label: 'Reconciliation', href: '/reconciliation', active: true },
    { icon: Settings, label: 'Settings', href: '/settings', active: false },
];

const SIDEBAR_MIN = 52;
const SIDEBAR_MAX = 300;
const SIDEBAR_DEFAULT = 220;
const SIDEBAR_COLLAPSE_THRESHOLD = 100;

const PERIOD_LABELS: Record<Period, string> = {
    '24h': 'Last 24 h',
    '7d': 'Last 7 days',
    '30d': 'Last 30 days',
    all: 'All time',
};

/* ─────────────────────────────────────────────
   Helpers
───────────────────────────────────────────── */
function formatNumber(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return n.toLocaleString();
}

function formatCost(usd: number): string {
    if (usd < 0.001) return `$${(usd * 100).toFixed(4)}¢`;
    return `$${usd.toFixed(4)}`;
}

function formatDate(iso: string): string {
    return new Date(iso).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function modelColor(model: string): string {
    if (model.includes('gemini')) return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300';
    if (model.includes('local') || model.includes('ollama')) return 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300';
    return 'bg-surface-container text-on-surface-variant';
}

/* ─────────────────────────────────────────────
   Mini bar sparkline (pure SVG, no lib)
───────────────────────────────────────────── */
function Sparkline({ data, color = 'var(--color-primary)' }: { data: number[]; color?: string }) {
    if (data.length < 2) return null;
    const max = Math.max(...data, 1);
    const w = 80;
    const h = 28;
    const step = w / (data.length - 1);
    const pts = data
        .map((v, i) => `${i * step},${h - (v / max) * h}`)
        .join(' ');
    return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
            <polyline
                points={pts}
                fill="none"
                stroke={color}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.7"
            />
        </svg>
    );
}

/* ─────────────────────────────────────────────
   Bar chart (tokens per session, horizontal)
───────────────────────────────────────────── */
function TokenBarChart({ records }: { records: TokenUsageRecord[] }) {
    if (records.length === 0) return null;
    const max = Math.max(...records.map((r) => r.total_tokens), 1);
    return (
        <div className="space-y-2">
            {records.slice(0, 10).map((r, i) => (
                <div key={r.session_id + i} className="flex items-center gap-3">
                    <span className="text-[11px] text-on-surface-variant w-20 truncate flex-shrink-0 font-mono">
                        {r.session_id.slice(-8)}
                    </span>
                    <div className="flex-1 h-4 bg-surface-container rounded-full overflow-hidden">
                        <div
                            className="h-full rounded-full bg-primary transition-all duration-700 ease-out"
                            style={{ width: `${(r.total_tokens / max) * 100}%`, opacity: 0.7 + 0.3 * (1 - i / records.length) }}
                        />
                    </div>
                    <span className="text-[11px] text-on-surface-variant w-14 text-right flex-shrink-0">
                        {formatNumber(r.total_tokens)}
                    </span>
                </div>
            ))}
        </div>
    );
}

/* ─────────────────────────────────────────────
   Donut chart (input vs output ratio)
───────────────────────────────────────────── */
function DonutChart({ input, output }: { input: number; output: number }) {
    const total = input + output || 1;
    const inputPct = (input / total) * 100;
    const r = 36;
    const circ = 2 * Math.PI * r;
    const inputArc = (inputPct / 100) * circ;

    return (
        <div className="flex items-center gap-4">
            <svg width={88} height={88} viewBox="0 0 88 88">
                <circle cx={44} cy={44} r={r} fill="none" stroke="var(--color-surface-container-high)" strokeWidth={10} />
                <circle
                    cx={44}
                    cy={44}
                    r={r}
                    fill="none"
                    stroke="var(--color-primary)"
                    strokeWidth={10}
                    strokeDasharray={`${inputArc} ${circ}`}
                    strokeLinecap="round"
                    transform="rotate(-90 44 44)"
                    opacity="0.85"
                />
                <circle
                    cx={44}
                    cy={44}
                    r={r}
                    fill="none"
                    stroke="var(--color-on-surface-variant)"
                    strokeWidth={10}
                    strokeDasharray={`${circ - inputArc} ${circ}`}
                    strokeDashoffset={-(inputArc)}
                    strokeLinecap="round"
                    transform="rotate(-90 44 44)"
                    opacity="0.35"
                />
                <text x={44} y={48} textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--color-on-surface)">
                    {Math.round(inputPct)}%
                </text>
            </svg>
            <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-primary opacity-85 flex-shrink-0" />
                    <span className="text-on-surface-variant">Input tokens</span>
                    <span className="ml-auto font-semibold text-on-surface">{formatNumber(input)}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-on-surface-variant opacity-35 flex-shrink-0" />
                    <span className="text-on-surface-variant">Output tokens</span>
                    <span className="ml-auto font-semibold text-on-surface">{formatNumber(output)}</span>
                </div>
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────────
   Stat card
───────────────────────────────────────────── */
interface StatCardProps {
    icon: LucideIcon;
    label: string;
    value: string;
    sub?: string;
    trend?: number; // positive = up, negative = down, 0 = flat
    sparkData?: number[];
}

function StatCard({ icon: Icon, label, value, sub, trend, sparkData }: StatCardProps) {
    const TrendIcon = trend == null ? null : trend > 0 ? ArrowUpRight : trend < 0 ? ArrowDownRight : Minus;
    const trendColor =
        trend == null ? '' : trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-500' : 'text-on-surface-variant';

    return (
        <div className="bg-surface-container-lowest border border-outline rounded-2xl p-4 shadow-sm flex flex-col gap-3 hover:shadow-md transition-shadow duration-200">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center flex-shrink-0">
                        <Icon size={16} className="text-on-surface-variant" />
                    </div>
                    <span className="text-xs font-medium text-on-surface-variant">{label}</span>
                </div>
                {sparkData && <Sparkline data={sparkData} />}
            </div>
            <div>
                <p className="text-2xl font-bold text-on-surface tracking-tight">{value}</p>
                {(sub || trend != null) && (
                    <div className="flex items-center gap-1 mt-0.5">
                        {TrendIcon && <TrendIcon size={12} className={trendColor} />}
                        {sub && <span className="text-[11px] text-on-surface-variant">{sub}</span>}
                    </div>
                )}
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────────
   Empty state
───────────────────────────────────────────── */
function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-on-surface-variant">
            <div className="w-14 h-14 rounded-2xl bg-surface-container border border-outline flex items-center justify-center">
                <BarChart2 size={24} className="opacity-40" />
            </div>
            <div className="text-center">
                <p className="text-sm font-medium text-on-surface opacity-60">No usage data yet</p>
                <p className="text-xs opacity-40 mt-1">Start a chat session to see token analytics here.</p>
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────────
   Error state
───────────────────────────────────────────── */
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 gap-4 text-on-surface-variant">
            <div className="w-12 h-12 rounded-2xl bg-error-container border border-outline flex items-center justify-center">
                <AlertCircle size={20} className="text-error" />
            </div>
            <div className="text-center">
                <p className="text-sm font-medium text-on-surface">Failed to load data</p>
                <p className="text-xs opacity-50 mt-1 max-w-xs">{message}</p>
            </div>
            <button
                onClick={onRetry}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline text-xs font-medium hover:bg-surface-container transition-colors"
            >
                <RefreshCw size={12} /> Retry
            </button>
        </div>
    );
}

/* ─────────────────────────────────────────────
   Sidebar (mirrors App.tsx sidebar)
───────────────────────────────────────────── */
interface SidebarProps {
    width: number;
    collapsed: boolean;
    darkMode: boolean;
    onToggleDark: () => void;
    onNewAnalysis: () => void;
}

function Sidebar({ width, collapsed, darkMode, onToggleDark, onNewAnalysis }: SidebarProps) {
    return (
        <aside
            className="flex flex-col flex-shrink-0 h-full border-r border-outline bg-surface-container-low overflow-hidden"
            style={{ width }}
        >
            <div
                className={`panel-header flex items-center gap-3 border-b border-outline flex-shrink-0 ${collapsed ? 'justify-center px-0' : 'px-4'
                    }`}
            >
                <div className="w-8 h-8 rounded-lg bg-primary text-on-primary flex items-center justify-center flex-shrink-0">
                    <FileText size={18} />
                </div>
                {!collapsed && (
                    <span className="font-semibold text-[17px] tracking-tight text-primary whitespace-nowrap overflow-hidden">
                        FinDoc AI
                    </span>
                )}
            </div>

            <nav className="flex-1 py-3 space-y-0.5 overflow-hidden">
                {NAV_ITEMS.map(({ icon: Icon, label, href, active }) => (
                    <Link
                        key={href}
                        to={href}
                        title={collapsed ? label : undefined}
                        className={`flex items-center gap-3 py-2 rounded-lg transition-colors font-medium overflow-hidden whitespace-nowrap ${collapsed ? 'justify-center mx-1 px-0' : 'mx-2 px-3'
                            } ${active
                                ? 'text-primary bg-surface-container-high'
                                : 'text-on-surface-variant hover:bg-surface-container-high'
                            }`}
                    >
                        <Icon size={20} className="flex-shrink-0" />
                        {!collapsed && <span className="text-sm font-medium truncate">{label}</span>}
                    </Link>
                ))}
            </nav>

            <div className={`panel-footer flex-shrink-0 border-t border-outline space-y-2 ${collapsed ? 'px-1' : 'px-3'}`}>
                {collapsed ? (
                    <button
                        title={darkMode ? 'Light mode' : 'Dark mode'}
                        onClick={onToggleDark}
                        className="w-full flex items-center justify-center p-2 rounded-lg border border-outline text-on-surface-variant hover:bg-surface-container-high transition-colors"
                    >
                        {darkMode ? <Sun size={18} /> : <Moon size={18} />}
                    </button>
                ) : (
                    <button
                        onClick={onToggleDark}
                        className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-outline text-on-surface-variant hover:bg-surface-container-high transition-colors"
                    >
                        <span className="text-sm font-medium">{darkMode ? 'Light mode' : 'Dark mode'}</span>
                        {darkMode ? <Sun size={16} /> : <Moon size={16} />}
                    </button>
                )}
                {collapsed ? (
                    <button
                        title="New Analysis"
                        onClick={onNewAnalysis}
                        className="w-full flex items-center justify-center bg-primary text-on-primary p-2 rounded-lg hover:opacity-90 transition-opacity"
                    >
                        <Plus size={20} />
                    </button>
                ) : (
                    <button
                        onClick={onNewAnalysis}
                        className="w-full flex items-center justify-center gap-2 bg-primary text-on-primary py-2 rounded-lg font-bold text-sm hover:opacity-90 transition-opacity"
                    >
                        <Plus size={18} />
                        New Analysis
                    </button>
                )}
            </div>
        </aside>
    );
}

/* ─────────────────────────────────────────────
   ResizeHandle (mirrors App.tsx)
───────────────────────────────────────────── */
function ResizeHandle({ onMouseDown }: { onMouseDown: (e: React.MouseEvent<HTMLDivElement>) => void }) {
    return (
        <div
            onMouseDown={onMouseDown}
            className="resize-handle relative flex-shrink-0 w-1 cursor-col-resize group z-10 bg-outline hover:bg-primary transition-colors duration-150"
        >
            <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-10 rounded-full bg-primary opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
        </div>
    );
}

function useResize(initial: number, min: number, max: number, direction: 1 | -1 = 1) {
    const [width, setWidth] = useState(initial);
    const dragging = useRef(false);
    const startX = useRef(0);
    const startW = useRef(0);

    useEffect(() => {
        const onMove = (e: MouseEvent) => {
            if (!dragging.current) return;
            const delta = (e.clientX - startX.current) * direction;
            setWidth(Math.min(max, Math.max(min, startW.current + delta)));
        };
        const onUp = () => {
            if (!dragging.current) return;
            dragging.current = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
        return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    }, [min, max, direction]);

    const onMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        e.preventDefault();
        dragging.current = true;
        startX.current = e.clientX;
        startW.current = width;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }, [width]);

    return [width, onMouseDown] as const;
}

/* ─────────────────────────────────────────────
   Period picker dropdown
───────────────────────────────────────────── */
function PeriodPicker({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
    const [open, setOpen] = useState(false);
    return (
        <div className="relative">
            <button
                onClick={() => setOpen((o) => !o)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline text-xs font-medium text-on-surface-variant hover:bg-surface-container transition-colors"
            >
                <Calendar size={12} />
                {PERIOD_LABELS[value]}
                <ChevronDown size={12} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>
            {open && (
                <div className="absolute right-0 top-full mt-1 z-50 w-36 bg-surface-container-lowest border border-outline rounded-xl shadow-lg overflow-hidden">
                    {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
                        <button
                            key={p}
                            onClick={() => { onChange(p); setOpen(false); }}
                            className={`w-full text-left px-3 py-2 text-xs font-medium transition-colors ${value === p ? 'bg-primary/10 text-primary' : 'text-on-surface hover:bg-surface-container'
                                }`}
                        >
                            {PERIOD_LABELS[p]}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

/* ─────────────────────────────────────────────
   Main Reconciliation page
───────────────────────────────────────────── */
export default function Reconciliation() {
    const navigate = useNavigate();
    const [darkMode, setDarkMode] = useState(
        () => localStorage.getItem('theme') === 'dark'
    ); const [sidebarWidth, onSidebarResize] = useResize(SIDEBAR_DEFAULT, SIDEBAR_MIN, SIDEBAR_MAX);
    const collapsed = sidebarWidth < SIDEBAR_COLLAPSE_THRESHOLD;

    const [period, setPeriod] = useState<Period>('7d');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [summary, setSummary] = useState<UsageSummary | null>(null);
    const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
    useEffect(() => {
        document.documentElement.classList.toggle('dark', darkMode);
        localStorage.setItem('theme', darkMode ? 'dark' : 'light');
    }, [darkMode]);

    const fetchUsage = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${BACKEND_URL}/api/usage?period=${period}`);
            if (!res.ok) throw new Error(`Server returned ${res.status}`);
            const data: UsageSummary = await res.json();
            setSummary(data);
            setLastRefresh(new Date());
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, [period]);

    useEffect(() => { fetchUsage(); }, [fetchUsage]);

    // Sparkline data: per-session total tokens in chronological order
    const sparkData = summary?.records.map((r) => r.total_tokens) ?? [];

    // Trend: compare first half vs second half of records
    const trendValue = (() => {
        if (!summary || summary.records.length < 2) return undefined;
        const mid = Math.floor(summary.records.length / 2);
        const older = summary.records.slice(0, mid).reduce((s, r) => s + r.total_tokens, 0);
        const newer = summary.records.slice(mid).reduce((s, r) => s + r.total_tokens, 0);
        if (older === 0) return 0;
        return ((newer - older) / older) * 100;
    })();

    const avgPerSession =
        summary && summary.session_count > 0
            ? Math.round(summary.total_tokens / summary.session_count)
            : 0;

    const handleExport = () => {
        if (!summary) return;
        const csv = [
            'session_id,timestamp,model,input_tokens,output_tokens,total_tokens,cost_usd',
            ...summary.records.map((r) =>
                [r.session_id, r.timestamp, r.model, r.input_tokens, r.output_tokens, r.total_tokens, r.cost_usd].join(','),
            ),
        ].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `token-usage-${period}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className={`flex h-screen w-screen overflow-hidden bg-background text-on-surface font-body-md ${darkMode ? 'dark' : ''}`}>
            <Sidebar
                width={sidebarWidth}
                collapsed={collapsed}
                darkMode={darkMode}
                onToggleDark={() => setDarkMode((d) => !d)}
                onNewAnalysis={() => navigate('/chat')}
            />
            <ResizeHandle onMouseDown={onSidebarResize} />

            {/* Main content */}
            <main className="flex flex-col flex-1 min-w-0 h-full overflow-hidden bg-background">

                {/* ── Header ── */}
                <div className="panel-header flex items-center justify-between px-6 border-b border-outline flex-shrink-0 bg-surface">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary flex-shrink-0">
                            <Landmark size={15} />
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-primary">Token Reconciliation</p>
                            <p className="text-xs text-on-surface-variant flex items-center gap-1">
                                {summary?.period_end ? (
                                    <><Clock size={10} className="flex-shrink-0" /> Updated {formatDate(summary.period_end)}</>
                                ) : 'Usage analytics'}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <PeriodPicker value={period} onChange={setPeriod} />
                        <button
                            onClick={fetchUsage}
                            disabled={loading}
                            title="Refresh"
                            className="p-1.5 rounded-lg border border-outline text-on-surface-variant hover:bg-surface-container disabled:opacity-40 transition-colors"
                        >
                            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        </button>
                        <button
                            onClick={handleExport}
                            disabled={!summary || summary.records.length === 0}
                            title="Export CSV"
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline text-xs font-medium text-on-surface-variant hover:bg-surface-container disabled:opacity-40 transition-colors"
                        >
                            <Download size={12} /> Export
                        </button>
                        <button className="p-1.5 hover:bg-surface-container-low rounded-full transition-colors">
                            <MoreVertical size={16} className="text-on-surface-variant" />
                        </button>
                    </div>
                </div>

                {/* ── Scrollable body ── */}
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">

                        {/* Skeleton / Error / Empty */}
                        {loading && !summary && (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {[...Array(4)].map((_, i) => (
                                    <div key={i} className="bg-surface-container-lowest border border-outline rounded-2xl p-4 h-28 animate-pulse" />
                                ))}
                            </div>
                        )}

                        {error && !loading && <ErrorState message={error} onRetry={fetchUsage} />}

                        {!loading && !error && summary && summary.records.length === 0 && <EmptyState />}

                        {summary && summary.records.length > 0 && (
                            <>
                                {/* Stat cards */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <StatCard
                                        icon={Zap}
                                        label="Total tokens"
                                        value={formatNumber(summary.total_tokens)}
                                        sub={trendValue != null ? `${trendValue >= 0 ? '+' : ''}${trendValue.toFixed(1)}% vs prev` : undefined}
                                        trend={trendValue}
                                        sparkData={sparkData}
                                    />
                                    <StatCard
                                        icon={TrendingUp}
                                        label="Avg / session"
                                        value={formatNumber(avgPerSession)}
                                        sub={`${summary.session_count} session${summary.session_count !== 1 ? 's' : ''}`}
                                    />
                                    <StatCard
                                        icon={Activity}
                                        label="Input tokens"
                                        value={formatNumber(summary.total_input)}
                                        sub={`${Math.round((summary.total_input / (summary.total_tokens || 1)) * 100)}% of total`}
                                    />
                                    <StatCard
                                        icon={BarChart2}
                                        label="Estimated cost"
                                        value={formatCost(summary.total_cost_usd)}
                                        sub="approx. based on model pricing"
                                    />
                                </div>

                                {/* Charts row */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                                    {/* Donut */}
                                    <div className="bg-surface-container-lowest border border-outline rounded-2xl p-5 shadow-sm">
                                        <div className="flex items-center justify-between mb-4">
                                            <p className="text-sm font-semibold text-on-surface">Token distribution</p>
                                            <span className="text-[11px] text-on-surface-variant">{PERIOD_LABELS[period]}</span>
                                        </div>
                                        <DonutChart input={summary.total_input} output={summary.total_output} />
                                    </div>

                                    {/* Bar chart */}
                                    <div className="bg-surface-container-lowest border border-outline rounded-2xl p-5 shadow-sm">
                                        <div className="flex items-center justify-between mb-4">
                                            <p className="text-sm font-semibold text-on-surface">Tokens per session</p>
                                            <span className="text-[11px] text-on-surface-variant">Top {Math.min(10, summary.records.length)}</span>
                                        </div>
                                        <TokenBarChart records={summary.records} />
                                    </div>
                                </div>

                                {/* Session table */}
                                <div className="bg-surface-container-lowest border border-outline rounded-2xl shadow-sm overflow-hidden">
                                    <div className="flex items-center justify-between px-5 py-3 border-b border-outline">
                                        <p className="text-sm font-semibold text-on-surface">Session breakdown</p>
                                        <span className="text-[11px] text-on-surface-variant">{summary.records.length} records</span>
                                    </div>
                                    <div className="overflow-x-auto custom-scrollbar">
                                        <table className="w-full text-xs">
                                            <thead>
                                                <tr className="bg-surface-container border-b border-outline">
                                                    <th className="text-left px-4 py-2.5 font-semibold text-on-surface-variant">Session</th>
                                                    <th className="text-left px-4 py-2.5 font-semibold text-on-surface-variant">Timestamp</th>
                                                    <th className="text-left px-4 py-2.5 font-semibold text-on-surface-variant">Model</th>
                                                    <th className="text-right px-4 py-2.5 font-semibold text-on-surface-variant">Input</th>
                                                    <th className="text-right px-4 py-2.5 font-semibold text-on-surface-variant">Output</th>
                                                    <th className="text-right px-4 py-2.5 font-semibold text-on-surface-variant">Total</th>
                                                    <th className="text-right px-4 py-2.5 font-semibold text-on-surface-variant">Cost</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {summary.records.map((r, i) => (
                                                    <tr
                                                        key={r.session_id + i}
                                                        className="border-b border-outline last:border-0 hover:bg-surface-container transition-colors"
                                                    >
                                                        <td className="px-4 py-2.5 font-mono text-on-surface-variant truncate max-w-[100px]">
                                                            …{r.session_id.slice(-10)}
                                                        </td>
                                                        <td className="px-4 py-2.5 text-on-surface-variant whitespace-nowrap">
                                                            {formatDate(r.timestamp)}
                                                        </td>
                                                        <td className="px-4 py-2.5">
                                                            <span className={`inline-block px-1.5 py-0.5 rounded-md text-[10px] font-semibold ${modelColor(r.model)}`}>
                                                                {r.model}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-2.5 text-right font-mono text-on-surface">
                                                            {formatNumber(r.input_tokens)}
                                                        </td>
                                                        <td className="px-4 py-2.5 text-right font-mono text-on-surface">
                                                            {formatNumber(r.output_tokens)}
                                                        </td>
                                                        <td className="px-4 py-2.5 text-right font-mono font-semibold text-on-surface">
                                                            {formatNumber(r.total_tokens)}
                                                        </td>
                                                        <td className="px-4 py-2.5 text-right font-mono text-on-surface-variant">
                                                            {formatCost(r.cost_usd)}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                            {/* Totals footer */}
                                            <tfoot>
                                                <tr className="bg-surface-container border-t-2 border-outline">
                                                    <td colSpan={3} className="px-4 py-2.5 font-semibold text-on-surface">
                                                        Total
                                                    </td>
                                                    <td className="px-4 py-2.5 text-right font-mono font-semibold text-on-surface">
                                                        {formatNumber(summary.total_input)}
                                                    </td>
                                                    <td className="px-4 py-2.5 text-right font-mono font-semibold text-on-surface">
                                                        {formatNumber(summary.total_output)}
                                                    </td>
                                                    <td className="px-4 py-2.5 text-right font-mono font-bold text-primary">
                                                        {formatNumber(summary.total_tokens)}
                                                    </td>
                                                    <td className="px-4 py-2.5 text-right font-mono font-semibold text-on-surface">
                                                        {formatCost(summary.total_cost_usd)}
                                                    </td>
                                                </tr>
                                            </tfoot>
                                        </table>
                                    </div>
                                </div>

                                {/* Footer note */}
                                <p className="text-[11px] text-on-surface-variant text-center pb-2">
                                    Cost estimates are approximate and based on public model pricing. Actual billing may differ.
                                </p>
                            </>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}