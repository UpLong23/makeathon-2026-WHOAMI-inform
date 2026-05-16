/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  Download,
  FileText,
  Landmark,
  LayoutDashboard,
  MessageSquare,
  Mic,
  Moon,
  MoreVertical,
  Paperclip,
  Plus,
  Send,
  Settings,
  Sparkles,
  Sun,
  Upload,
  X,
  LucideIcon,
} from 'lucide-react';
import React, {
  useState,
  useRef,
  useCallback,
  useEffect,
  MouseEvent,
  DragEvent,
  ChangeEvent,
} from 'react';

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
interface UploadedFile {
  id: number;
  name: string;
  type: string;
  url: string;
}

interface Message {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  files?: UploadedFile[];
  timestamp: Date;
}

interface NavItem {
  icon: LucideIcon;
  label: string;
  active: boolean;
}

/* ─────────────────────────────────────────────
   Constants
───────────────────────────────────────────── */
const MAX_FILE_MB = 10;
const ALLOWED_TYPES: string[] = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/jpg',
  'image/webp',
];

const SIDEBAR_MIN = 52;
const SIDEBAR_MAX = 300;
const SIDEBAR_DEFAULT = 220;
const SIDEBAR_COLLAPSE_THRESHOLD = 100;

const CHAT_MIN = 300;
const CHAT_MAX = 620;
const CHAT_DEFAULT = 420;

const BACKEND_URL = 'http://127.0.0.1:8000';

const NAV_ITEMS: NavItem[] = [
  { icon: LayoutDashboard, label: 'Dashboard', active: false },
  { icon: MessageSquare, label: 'Chat Assistant', active: true },
  { icon: Landmark, label: 'Reconciliation', active: false },
  { icon: Settings, label: 'Settings', active: false },
];

const QUICK_PROMPTS: { label: string; text: string }[] = [
  { label: '🧾 Parse a receipt', text: 'Paste a receipt and extract all line items into a table' },
  { label: '➗ Split a bill', text: 'Split a €120 dinner bill equally between 4 people' },
  { label: '💰 Track my spending', text: 'What is my total spend so far this session?' },
  { label: '🔍 Find duplicates', text: 'Check these receipts for any duplicate charges' },
];

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function makeSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/* ─────────────────────────────────────────────
   useResize hook
───────────────────────────────────────────── */
function useResize(
  initial: number,
  min: number,
  max: number,
): [number, (e: MouseEvent<HTMLDivElement>) => void] {
  const [width, setWidth] = useState<number>(initial);
  const dragging = useRef<boolean>(false);
  const startX = useRef<number>(0);
  const startW = useRef<number>(0);

  const onMouseDown = useCallback(
    (e: MouseEvent<HTMLDivElement>) => {
      e.preventDefault();
      dragging.current = true;
      startX.current = e.clientX;
      startW.current = width;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },
    [width],
  );

  useEffect(() => {
    const onMove = (e: globalThis.MouseEvent) => {
      if (!dragging.current) return;
      const delta = e.clientX - startX.current;
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
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [min, max]);

  return [width, onMouseDown];
}

/* ─────────────────────────────────────────────
   ResizeHandle
───────────────────────────────────────────── */
interface ResizeHandleProps {
  onMouseDown: (e: MouseEvent<HTMLDivElement>) => void;
}

function ResizeHandle({ onMouseDown }: ResizeHandleProps) {
  return (
    <div
      onMouseDown={onMouseDown}
      className="resize-handle relative flex-shrink-0 w-1 cursor-col-resize group z-10 bg-outline hover:bg-primary transition-colors duration-150"
    >
      <div className="absolute inset-y-0 -left-2 -right-2" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-10 rounded-full bg-primary opacity-0 group-hover:opacity-100 transition-opacity duration-150" />
    </div>
  );
}

/* ─────────────────────────────────────────────
   App
───────────────────────────────────────────── */
export default function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [sessionId, setSessionId] = useState<string>(makeSessionId);

  const [sidebarWidth, onSidebarResize] = useResize(SIDEBAR_DEFAULT, SIDEBAR_MIN, SIDEBAR_MAX);
  const [chatWidth, onChatResize] = useResize(CHAT_DEFAULT, CHAT_MIN, CHAT_MAX);

  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [stagedFiles, setStagedFiles] = useState<UploadedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null);

  /* dark mode */
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  /* file staging */
  const addFiles = useCallback((files: FileList) => {
    Array.from(files).forEach((file) => {
      if (!ALLOWED_TYPES.includes(file.type)) return;
      if (file.size > MAX_FILE_MB * 1024 * 1024) return;
      const url = URL.createObjectURL(file);
      setStagedFiles((prev) => [
        ...prev,
        { id: Date.now() + Math.random(), name: file.name, type: file.type, url },
      ]);
    });
  }, []);

  const removeStaged = useCallback(
    (id: number) => {
      setStagedFiles((prev) => {
        const f = prev.find((x) => x.id === id);
        if (f && (!selectedFile || selectedFile.id !== f.id)) URL.revokeObjectURL(f.url);
        return prev.filter((x) => x.id !== id);
      });
    },
    [selectedFile],
  );

  /* new analysis — wipes backend memory and resets UI */
  const handleNewAnalysis = useCallback(() => {
    fetch(`${BACKEND_URL}/api/session/${sessionId}`, { method: 'DELETE' }).catch(() => { });
    setSessionId(makeSessionId());
    setMessages([]);
    setStagedFiles([]);
    setSelectedFile(null);
    setIsTyping(false);
    setIsProcessing(false);
  }, [sessionId]);

  /* send message to backend */
  const handleSend = useCallback(
    (text: string, refocusTextarea: () => void) => {
      const trimmed = text.trim();
      if (!trimmed && stagedFiles.length === 0) return;

      const userMsg: Message = {
        id: Date.now(),
        role: 'user',
        text: trimmed,
        files: stagedFiles.length > 0 ? [...stagedFiles] : undefined,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setStagedFiles([]);
      refocusTextarea();
      setIsTyping(true);
      setIsProcessing(true);

      const aiId = Date.now() + 1;
      let isFirstToken = true;

      fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, session_id: sessionId }),
      })
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const reader = res.body!.getReader();
          const decoder = new TextDecoder();

          const pump = (): Promise<void> =>
            reader.read().then(({ done, value }) => {
              if (done) {
                setIsTyping(false);
                setIsProcessing(false);
                return;
              }

              const raw = decoder.decode(value, { stream: true });
              const lines = raw.split('\n');

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const token = line.slice(6);
                  if (isFirstToken) {
                    setIsTyping(false);
                    setMessages((prev) => [
                      ...prev,
                      { id: aiId, role: 'assistant', text: token, timestamp: new Date() },
                    ]);
                    isFirstToken = false;
                  } else {
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === aiId ? { ...m, text: m.text + token } : m,
                      ),
                    );
                  }
                }
              }

              return pump();
            });

          return pump();
        })
        .catch((err) => {
          setIsTyping(false);
          setIsProcessing(false);
          if (isFirstToken) {
            setMessages((prev) => [
              ...prev,
              {
                id: aiId,
                role: 'assistant',
                text: `⚠️ Error: ${err.message}`,
                timestamp: new Date(),
              },
            ]);
          } else {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId
                  ? { ...m, text: m.text + `\n⚠️ Error: ${err.message}` }
                  : m,
              ),
            );
          }
        });
    },
    [stagedFiles, sessionId],
  );

  const collapsed = sidebarWidth < SIDEBAR_COLLAPSE_THRESHOLD;
  const previewOpen = selectedFile !== null;

  return (
    <div className={`flex h-screen w-screen overflow-hidden bg-background text-on-surface font-body-md selection:bg-secondary-fixed ${darkMode ? 'dark' : ''}`}>
      <Sidebar
        width={sidebarWidth}
        collapsed={collapsed}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode((d) => !d)}
        onNewAnalysis={handleNewAnalysis}
      />
      <ResizeHandle onMouseDown={onSidebarResize} />
      <ChatPanel
        width={previewOpen ? chatWidth : undefined}
        messages={messages}
        isTyping={isTyping}
        isProcessing={isProcessing}
        stagedFiles={stagedFiles}
        selectedFile={selectedFile}
        setSelectedFile={setSelectedFile}
        addFiles={addFiles}
        removeStaged={removeStaged}
        handleSend={handleSend}
      />
      {previewOpen && (
        <>
          <ResizeHandle onMouseDown={onChatResize} />
          <DocumentPreview selectedFile={selectedFile} setSelectedFile={setSelectedFile} />
        </>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Sidebar
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
        {NAV_ITEMS.map(({ icon: Icon, label, active }) => (
          <a
            key={label}
            href="#"
            title={collapsed ? label : undefined}
            className={`flex items-center gap-3 py-2 rounded-lg transition-colors font-medium overflow-hidden whitespace-nowrap ${collapsed ? 'justify-center mx-1 px-0' : 'mx-2 px-3'
              } ${active
                ? 'text-primary bg-surface-container-high'
                : 'text-on-surface-variant hover:bg-surface-container-high'
              }`}
          >
            <Icon size={20} className="flex-shrink-0" />
            {!collapsed && <span className="text-sm font-medium truncate">{label}</span>}
          </a>
        ))}
      </nav>

      {/* Footer actions */}
      <div className={`py-4 flex-shrink-0 border-t border-outline space-y-2 ${collapsed ? 'px-1' : 'px-3'}`}>
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
   TypingIndicator
───────────────────────────────────────────── */
function TypingIndicator() {
  return (
    <div className="flex flex-col items-start">
      <div className="flex items-start gap-2">
        <div className="w-7 h-7 rounded-full border border-outline bg-surface-container-lowest flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
          <Sparkles size={13} className="text-primary" />
        </div>
        <div className="bg-surface-container-lowest border border-outline px-4 py-3.5 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-on-surface-variant animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-on-surface-variant animate-bounce [animation-delay:150ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-on-surface-variant animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   ChatPanel
───────────────────────────────────────────── */
interface ChatPanelProps {
  width?: number;
  messages: Message[];
  isTyping: boolean;
  isProcessing: boolean;
  stagedFiles: UploadedFile[];
  selectedFile: UploadedFile | null;
  setSelectedFile: (f: UploadedFile | null) => void;
  addFiles: (files: FileList) => void;
  removeStaged: (id: number) => void;
  handleSend: (text: string, refocus: () => void) => void;
}

function ChatPanel({
  width,
  messages,
  isTyping,
  isProcessing,
  stagedFiles,
  selectedFile,
  setSelectedFile,
  addFiles,
  removeStaged,
  handleSend,
}: ChatPanelProps) {
  const [draft, setDraft] = useState('');
  const [dragActive, setDragActive] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const focusTextarea = useCallback(() => {
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setDragActive(true); };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setDragActive(false); };
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files) addFiles(e.dataTransfer.files);
  };
  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(e.target.files);
    e.target.value = '';
  };

  const submit = useCallback(() => {
    if (isProcessing) return;
    if (!draft.trim() && stagedFiles.length === 0) return;
    handleSend(draft, focusTextarea);
    setDraft('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }, [draft, stagedFiles, handleSend, focusTextarea, isProcessing]);

  const chipLabel = (mime: string) => (mime === 'application/pdf' ? 'PDF' : 'IMG');
  const chipClass = (mime: string) =>
    mime === 'application/pdf' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800';

  const canSend = !isProcessing && (!!draft.trim() || stagedFiles.length > 0);

  const panelStyle: React.CSSProperties =
    width !== undefined ? { width, flexShrink: 0 } : { flex: 1, minWidth: CHAT_MIN };

  const statusDot = isTyping ? 'bg-amber-400' : 'bg-green-500';

  const statusLabel = isTyping ? 'Typing…' : 'Online';

  return (
    <section className="flex flex-col h-full bg-surface overflow-hidden" style={panelStyle}>

      {/* ── Header ── */}
      <div className="panel-header flex items-center justify-between px-4 border-b border-outline flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary flex-shrink-0">
            <Sparkles size={15} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-primary truncate">Analysis Assistant</p>
            <p className="text-xs text-on-surface-variant flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${statusDot}`} />
              {statusLabel}
            </p>
          </div>
        </div>
        <button className="flex-shrink-0 p-1.5 hover:bg-surface-container-low rounded-full transition-colors">
          <MoreVertical size={16} className="text-on-surface-variant" />
        </button>
      </div>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 bg-background custom-scrollbar">

        {/* ── Empty state with suggestion bubbles ── */}
        {messages.length === 0 && !isTyping && (
          <div className="flex flex-col items-center justify-center h-full gap-6 select-none">

            {/* Icon + greeting */}
            <div className="flex flex-col items-center gap-2">
              <div className="w-11 h-11 rounded-2xl bg-surface-container-low border border-outline flex items-center justify-center">
                <Sparkles size={20} className="text-on-surface-variant opacity-50" />
              </div>
              <p className="text-sm font-medium text-on-surface opacity-60">How can I help you?</p>
            </div>

            {/* 2×2 suggestion bubbles */}
            <div className="grid grid-cols-2 gap-2.5" style={{ width: '100%', maxWidth: '400px' }}>
              {QUICK_PROMPTS.map(({ label, text }) => (
                <button
                  key={label}
                  onClick={() => handleSend(text, focusTextarea)}
                  className="flex flex-col gap-1 text-left px-4 py-3 rounded-2xl border border-outline bg-surface-container-lowest hover:bg-surface-container hover:border-on-surface/20 active:scale-[0.97] transition-all duration-150 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <span className="text-xs font-semibold text-on-surface">{label}</span>
                  <span className="text-[11px] text-on-surface-variant leading-snug">{text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Message list ── */}
        {messages.map((msg) =>
          msg.role === 'user' ? (
            <div key={msg.id} className="flex flex-col items-end">
              {msg.files && msg.files.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-1.5 justify-end">
                  {msg.files.map((f) => (
                    <button
                      key={f.id}
                      onClick={() => setSelectedFile(selectedFile?.id === f.id ? null : f)}
                      className={`inline-flex items-center gap-1.5 border rounded-lg px-2 py-1 transition-colors ${selectedFile?.id === f.id
                        ? 'border-primary/50 bg-primary/10'
                        : 'border-outline bg-surface hover:bg-surface-container-high'
                        }`}
                    >
                      <span className={`text-[10px] font-bold px-1 py-0.5 rounded-sm ${chipClass(f.type)}`}>
                        {chipLabel(f.type)}
                      </span>
                      <span className="text-xs text-on-surface truncate max-w-[110px]">{f.name}</span>
                    </button>
                  ))}
                </div>
              )}
              {msg.text && (
                <div className="bg-primary text-on-primary px-4 py-2.5 rounded-2xl rounded-tr-sm max-w-[88%] shadow-sm">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                </div>
              )}
              <span className="text-[11px] text-on-surface-variant mt-1 mr-1">
                {formatTime(msg.timestamp)}
              </span>
            </div>
          ) : (
            <div key={msg.id} className="flex flex-col items-start">
              <div className="flex items-start gap-2 max-w-[92%]">
                <div className="w-7 h-7 rounded-full border border-outline bg-surface-container-lowest flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                  <Sparkles size={13} className="text-primary" />
                </div>
                <div className="bg-surface-container-lowest border border-outline px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm">
                  <p className="text-sm leading-relaxed text-on-surface whitespace-pre-wrap">{msg.text}</p>
                </div>
              </div>
              <span className="text-[11px] text-on-surface-variant mt-1 ml-9 tracking-wide">
                AI Assistant · {formatTime(msg.timestamp)}
              </span>
            </div>
          ),
        )}

        {isTyping && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="px-3 pb-3 pt-2 bg-surface flex-shrink-0 w-1/2 mx-auto">
        <div
          className={`relative rounded-2xl transition-all duration-150 ${dragActive
            ? 'border-2 border-dashed border-primary bg-primary/5'
            : 'border border-outline bg-surface-container-lowest shadow-[0_2px_16px_rgba(0,0,0,0.07)] focus-within:border-primary focus-within:shadow-[0_2px_20px_rgba(0,0,0,0.11)]'
            }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {dragActive && (
            <div className="absolute inset-0 rounded-2xl flex flex-col items-center justify-center gap-1 pointer-events-none z-10">
              <Upload size={20} className="text-primary" />
              <span className="text-sm font-medium text-primary">Drop to attach</span>
              <span className="text-xs text-on-surface-variant">JPG, PNG or PDF · max 10 MB</span>
            </div>
          )}

          {stagedFiles.length > 0 && (
            <div className="flex flex-wrap gap-1.5 px-3 pt-2.5">
              {stagedFiles.map((f) => (
                <div
                  key={f.id}
                  onClick={() => setSelectedFile(selectedFile?.id === f.id ? null : f)}
                  className={`inline-flex items-center gap-1.5 bg-surface border rounded-lg px-2 py-1 cursor-pointer transition-colors ${selectedFile?.id === f.id
                    ? 'border-primary/50 bg-primary/5'
                    : 'border-outline hover:bg-surface-container-high'
                    }`}
                >
                  <span className={`text-[10px] font-bold px-1 py-0.5 rounded-sm ${chipClass(f.type)}`}>
                    {chipLabel(f.type)}
                  </span>
                  <span className="text-xs text-on-surface truncate max-w-[120px]">{f.name}</span>
                  <button
                    className="text-on-surface-variant hover:text-on-surface ml-0.5 transition-colors"
                    onClick={(e: MouseEvent) => { e.stopPropagation(); removeStaged(f.id); }}
                  >
                    <X size={11} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Main row: attach | textarea | mic | send */}
          <div className="flex items-end gap-1.5 px-2 py-2 w-full">
            <button
              title="Attach file"
              onClick={() => fileInputRef.current?.click()}
              className="flex-shrink-0 p-1.5 rounded-lg text-on-surface-variant hover:text-primary hover:bg-surface-container-high transition-colors"
            >
              <Paperclip size={17} />
            </button>

            <textarea
              ref={textareaRef}
              value={draft}
              onChange={(e) => {
                setDraft(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
              rows={1}
              className="flex-1 min-w-0 bg-transparent border-none focus:ring-0 resize-none text-sm placeholder:text-on-surface-variant outline-none disabled:opacity-50 py-1.5 leading-relaxed overflow-hidden"
              style={{ minHeight: '28px', maxHeight: '120px' }}
              placeholder={
                stagedFiles.length > 0
                  ? 'Add a question about these documents…'
                  : 'Ask anything, or drag & drop a file…'
              }
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
              }}
            />

            <div className="flex items-center gap-1.5 ml-auto">
              <button
                title="Voice"
                className="flex-shrink-0 p-1.5 rounded-lg text-on-surface-variant hover:text-primary hover:bg-surface-container-high transition-colors"
              >
                <Mic size={17} />
              </button>

              <button
                onMouseDown={(e: MouseEvent<HTMLButtonElement>) => e.preventDefault()}
                onClick={submit}
                disabled={!canSend}
                className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-xl bg-primary text-on-primary shadow-sm hover:opacity-90 active:scale-95 transition-all duration-100 disabled:opacity-25 disabled:cursor-not-allowed disabled:shadow-none"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp"
          multiple
          className="hidden"
          onChange={handleFileInput}
        />

        <p className="text-[11px] text-on-surface-variant text-center mt-1.5">
          AI analysis can make mistakes. Verify important information.
        </p>
      </div>

    </section>
  );
}

/* ─────────────────────────────────────────────
   DocumentPreview
───────────────────────────────────────────── */
interface DocumentPreviewProps {
  selectedFile: UploadedFile | null;
  setSelectedFile: (f: UploadedFile | null) => void;
}

function DocumentPreview({ selectedFile, setSelectedFile }: DocumentPreviewProps) {
  const isPdf = selectedFile?.type === 'application/pdf';

  return (
    <section className="flex-1 min-w-[180px] flex flex-col overflow-hidden bg-surface-container-low">
      <div className="flex-1 m-4 bg-surface-container-lowest border border-outline rounded-2xl flex flex-col overflow-hidden shadow-sm">
        <div className="preview-toolbar flex items-center justify-between px-4 border-b border-outline flex-shrink-0 bg-surface-container-lowest">
          <div className="flex items-center gap-2 min-w-0">
            <FileText size={16} className="text-on-surface-variant flex-shrink-0" />
            <span className="text-sm font-medium truncate text-primary">
              {selectedFile ? selectedFile.name : 'Document Preview'}
            </span>
          </div>
          {selectedFile && (
            <div className="flex items-center gap-1 flex-shrink-0">
              <a
                href={selectedFile.url}
                download={selectedFile.name}
                className="p-1.5 hover:bg-surface-container-low rounded-lg transition-colors flex items-center justify-center"
                title="Download"
              >
                <Download size={16} className="text-on-surface-variant" />
              </a>
              <button
                onClick={() => setSelectedFile(null)}
                className="p-1.5 hover:bg-surface-container-low rounded-lg transition-colors flex items-center justify-center"
                title="Close preview"
              >
                <X size={16} className="text-on-surface-variant" />
              </button>
            </div>
          )}
        </div>

        {selectedFile ? (
          <div className="flex-1 overflow-auto p-4 flex justify-center items-start custom-scrollbar">
            {isPdf ? (
              <embed
                src={selectedFile.url}
                type="application/pdf"
                className="preview-pdf w-full rounded-lg shadow-md border border-outline-variant"
              />
            ) : (
              <img
                src={selectedFile.url}
                alt={selectedFile.name}
                className="preview-image max-w-full rounded-lg shadow-md border border-outline-variant object-contain"
              />
            )}
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-on-surface-variant px-6">
            <div className="w-14 h-14 rounded-2xl bg-surface-container-low border border-outline flex items-center justify-center">
              <FileText size={26} className="opacity-40" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium">No document selected</p>
              <p className="text-xs opacity-60 mt-1 max-w-[180px] leading-relaxed">
                Drop a file in the chat or click a file chip to preview it here
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs opacity-40 font-medium">
              <span>JPG</span><span>·</span><span>PNG</span><span>·</span><span>PDF</span>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}