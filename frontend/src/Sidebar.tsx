/**
 * Sidebar.tsx — shared sidebar with react-router-dom navigation
 * Used by both App.tsx and Reconciliation.tsx
 */

import { Link, useLocation } from 'react-router-dom';
import {
    FileText,
    Landmark,
    LayoutDashboard,
    MessageSquare,
    Moon,
    Plus,
    Settings,
    Sun,
    LucideIcon,
} from 'lucide-react';

interface NavItem {
    icon: LucideIcon;
    label: string;
    to: string;
}

const NAV_ITEMS: NavItem[] = [
    { icon: LayoutDashboard, label: 'Dashboard', to: '/dashboard' },
    { icon: MessageSquare, label: 'Chat Assistant', to: '/chat' },
    { icon: Landmark, label: 'Reconciliation', to: '/reconciliation' },
    { icon: Settings, label: 'Settings', to: '/settings' },
];

interface SidebarProps {
    width: number;
    collapsed: boolean;
    darkMode: boolean;
    onToggleDark: () => void;
    onNewAnalysis: () => void;
}

export default function Sidebar({
    width,
    collapsed,
    darkMode,
    onToggleDark,
    onNewAnalysis,
}: SidebarProps) {
    const { pathname } = useLocation();

    return (
        <aside
            className="flex flex-col flex-shrink-0 h-full border-r border-outline bg-surface-container-low overflow-hidden"
            style={{ width }}
        >
            {/* Logo */}
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

            {/* Nav */}
            <nav className="flex-1 py-3 space-y-0.5 overflow-hidden">
                {NAV_ITEMS.map(({ icon: Icon, label, to }) => {
                    const active = pathname === to || (to === '/chat' && pathname === '/');
                    return (
                        <Link
                            key={to}
                            to={to}
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
                    );
                })}
            </nav>

            {/* Footer */}
            <div
                className={`panel-footer flex-shrink-0 border-t border-outline space-y-2 ${collapsed ? 'px-1' : 'px-3'
                    }`}
            >
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