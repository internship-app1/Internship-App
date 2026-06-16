import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { SignInButton, useAuth } from '@clerk/react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import { API_BASE_URL } from '../lib/api';
import { SavedJob, SavedJobStatus } from '../types';

// ── constants ────────────────────────────────────────────────────────────────

const STATUSES: { key: SavedJobStatus; label: string; emoji: string; color: string }[] = [
  { key: 'saved',        label: 'Saved',        emoji: '🔖', color: '#818CF8' },
  { key: 'interested',   label: 'Interested',   emoji: '👀', color: '#38BDF8' },
  { key: 'applied',      label: 'Applied',      emoji: '📨', color: '#A78BFA' },
  { key: 'interviewing', label: 'Interviewing', emoji: '💬', color: '#FBBF24' },
  { key: 'offer',        label: 'Offer',        emoji: '🎉', color: '#34D399' },
  { key: 'rejected',     label: 'Rejected',     emoji: '✋', color: '#FB7185' },
  { key: 'ghosted',      label: 'Ghosted',      emoji: '👻', color: '#94A3B8' },
];

const QUICK_TAGS = [
  { emoji: '📞', label: 'Recruiter call' },
  { emoji: '🤝', label: 'Referral' },
  { emoji: '🔔', label: 'Follow up' },
  { emoji: '✅', label: 'OA done' },
];

// ── helpers ──────────────────────────────────────────────────────────────────

function hexA(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function isoDate(d: Date): string {
  const z = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

function parseIsoDate(s: string): Date {
  const [y, mo, dd] = s.split('-').map(Number);
  return new Date(y, mo - 1, dd);
}

function normalizeDeadline(raw?: string | null): string | null {
  if (!raw) return null;
  return raw.includes('T') ? raw.split('T')[0] : raw;
}

function countdown(isoStr: string): { label: string; color: string } {
  const d = parseIsoDate(isoStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((d.getTime() - today.getTime()) / 86400000);
  const color = days <= 6 ? '#FB7185' : days <= 14 ? '#FBBF24' : '#34D399';
  const mon = d.toLocaleDateString('en-US', { month: 'short' });
  let label: string;
  if (days < 0) label = `${Math.abs(days)}d overdue · ${mon} ${d.getDate()}`;
  else if (days === 0) label = `Due today · ${mon} ${d.getDate()}`;
  else if (days === 1) label = `Due tomorrow · ${mon} ${d.getDate()}`;
  else label = `${days} days left · ${mon} ${d.getDate()}`;
  return { label, color };
}

function scoreRingColor(score: number): string {
  return score >= 85 ? '#34D399' : score >= 70 ? '#FBBF24' : '#FB7185';
}

// ── Injected CSS ─────────────────────────────────────────────────────────────

const TRACKER_CSS = `
  @keyframes sjspin  { to { transform: rotate(360deg); } }
  @keyframes sjblink { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.7)} }
  @keyframes sjmenuin { from{opacity:0;transform:translateY(-6px) scale(.96)} to{opacity:1;transform:none} }
  @keyframes sjpop { 0%{transform:scale(.4) rotate(-12deg);opacity:.2} 55%{transform:scale(1.28) rotate(6deg)} 100%{transform:scale(1) rotate(0);opacity:1} }
  .sj-card-enter { animation: sjcardin .22s ease both; }
  @keyframes sjcardin { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:none} }
  .sj-pill:hover  { filter: brightness(1.08); }
  .sj-pill:active { transform: scale(.96); }
  .sj-tag-btn:hover  { background: #222E44 !important; color: #fff !important; border-color: #3A496A !important; }
  .sj-tag-btn:active { transform: scale(.94); }
  .sj-dl-btn:hover { filter: brightness(1.08); }
  .sj-cal-day:hover { background: #222E44 !important; color: #fff !important; }
  .sj-preset:hover  { background: #222E44 !important; color: #fff !important; border-color: #3A496A !important; }
  .sj-nav-btn:hover { background: #222E44 !important; color: #fff !important; }
  .sj-filter-tab { transition: background .15s, border-color .15s, color .15s; }
  .sj-filter-tab:hover { border-color: rgba(148,163,184,0.3) !important; color: #E2E8F0 !important; }
  .sj-notes-ta::placeholder { color: #475569; }
`;

// ── Calendar Picker ───────────────────────────────────────────────────────────

interface CalPickerProps {
  value: string | null;
  onPick: (iso: string) => void;
  onClear: () => void;
}

function CalPicker({ value, onPick, onClear }: CalPickerProps) {
  const init = value ? parseIsoDate(value) : new Date();
  const [vy, setVy] = useState(init.getFullYear());
  const [vm, setVm] = useState(init.getMonth());
  const todayIso = isoDate(new Date());

  const prev = () => {
    if (vm === 0) { setVy(y => y - 1); setVm(11); } else setVm(m => m - 1);
  };
  const next = () => {
    if (vm === 11) { setVy(y => y + 1); setVm(0); } else setVm(m => m + 1);
  };

  const calLabel = new Date(vy, vm, 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const startDow = new Date(vy, vm, 1).getDay();
  const daysInMonth = new Date(vy, vm + 1, 0).getDate();

  const pickPreset = (days: number) => {
    const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + days);
    onPick(isoDate(d)); setVy(d.getFullYear()); setVm(d.getMonth());
  };
  const pickMonthEnd = () => onPick(isoDate(new Date(vy, vm + 1, 0)));

  const navBtn: React.CSSProperties = {
    width: 28, height: 28, borderRadius: 8, border: '1px solid #2C3852',
    background: '#1B2435', color: '#AEB9CC', cursor: 'pointer',
    display: 'grid', placeItems: 'center', fontSize: 15,
  };

  return (
    <div style={{
      position: 'absolute', top: 'calc(100% + 6px)', right: 0, zIndex: 30,
      width: 286, padding: 14, background: '#161E2E', border: '1px solid #2A3650',
      borderRadius: 16, boxShadow: '0 20px 50px -18px rgba(0,0,0,.75)',
      animation: 'sjmenuin .18s cubic-bezier(.2,.9,.3,1.2)', transformOrigin: 'top right',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <button onClick={prev} className="sj-nav-btn" style={navBtn}>‹</button>
        <div style={{ flex: 1, textAlign: 'center', fontSize: 13.5, fontWeight: 600, color: '#EAEFF7', letterSpacing: '-0.01em', whiteSpace: 'nowrap' }}>
          {calLabel}
        </div>
        <button onClick={next} className="sj-nav-btn" style={navBtn}>›</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 2, marginBottom: 4 }}>
        {['S','M','T','W','T','F','S'].map((d, i) => (
          <div key={i} style={{ textAlign: 'center', fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: '#5E6B82' }}>{d}</div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 2 }}>
        {Array.from({ length: startDow }, (_, i) => (
          <span key={`b${i}`} style={{ aspectRatio: '1' }} />
        ))}
        {Array.from({ length: daysInMonth }, (_, i) => {
          const dd = i + 1;
          const iso = isoDate(new Date(vy, vm, dd));
          const isSel = iso === value;
          const isToday = iso === todayIso && !isSel;
          return (
            <button key={dd} onClick={() => onPick(iso)} className="sj-cal-day" style={{
              position: 'relative', aspectRatio: '1', border: 0, borderRadius: 8, cursor: 'pointer',
              display: 'grid', placeItems: 'center', minWidth: 0,
              fontFamily: "'Source Sans 3',system-ui,sans-serif", fontSize: 12.5,
              fontWeight: isSel || isToday ? 700 : 500,
              background: isSel ? '#C2F45C' : 'transparent',
              color: isSel ? '#15200A' : isToday ? '#C2F45C' : '#C4CDDD',
              transition: 'background .14s, color .14s',
            }}>
              {dd}
              {isToday && (
                <span style={{ position: 'absolute', bottom: 3, left: '50%', transform: 'translateX(-50%)', width: 3, height: 3, borderRadius: '50%', background: '#C2F45C' }} />
              )}
            </button>
          );
        })}
      </div>

      <div style={{ display: 'flex', gap: 6, marginTop: 13, paddingTop: 13, borderTop: '1px solid #232F45' }}>
        {[{ label: '+1 week', days: 7 }, { label: '+2 weeks', days: 14 }].map(p => (
          <button key={p.label} onClick={() => pickPreset(p.days)} className="sj-preset" style={{
            flex: '1 1 auto', height: 28, padding: '0 8px', borderRadius: 8,
            background: '#1B2435', border: '1px solid #2C3852', color: '#AEB9CC',
            fontFamily: "'JetBrains Mono',monospace", fontSize: 11, cursor: 'pointer', whiteSpace: 'nowrap',
          }}>{p.label}</button>
        ))}
        <button onClick={pickMonthEnd} className="sj-preset" style={{
          flex: '1 1 auto', height: 28, padding: '0 8px', borderRadius: 8,
          background: '#1B2435', border: '1px solid #2C3852', color: '#AEB9CC',
          fontFamily: "'JetBrains Mono',monospace", fontSize: 11, cursor: 'pointer', whiteSpace: 'nowrap',
        }}>Month end</button>
      </div>

      {value && (
        <button onClick={onClear} style={{
          width: '100%', marginTop: 8, height: 28, borderRadius: 8,
          background: 'transparent', border: 'none', color: '#F0808A',
          fontFamily: "'Source Sans 3',system-ui,sans-serif", fontSize: 12, fontWeight: 600, cursor: 'pointer',
        }}>Clear deadline</button>
      )}
    </div>
  );
}

// ── Tracker Card ──────────────────────────────────────────────────────────────

interface TrackerCardProps {
  row: SavedJob;
  token: string | null;
  onUpdate: (updated: SavedJob) => void;
}

function TrackerCard({ row, token, onUpdate }: TrackerCardProps) {
  const [localNotes, setLocalNotes] = useState(row.notes || '');
  const [notesActive, setNotesActive] = useState(false);
  const [saveState, setSaveState] = useState<'saving' | 'saved' | null>(null);
  const [dlOpen, setDlOpen] = useState(false);
  const [emojiKey, setEmojiKey] = useState(0);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { setLocalNotes(row.notes || ''); }, [row.notes]);

  const sm = STATUSES.find(s => s.key === row.status) ?? STATUSES[0];
  const dl = normalizeDeadline(row.deadline);
  const cd = dl ? countdown(dl) : null;
  const uc = cd ? cd.color : '#94A3B8';

  const rawScore = row.job?.score ?? row.job?.match_score ?? 0;
  const score = rawScore > 1 ? Math.round(rawScore) : Math.round(rawScore * 100);
  const rc = scoreRingColor(score);
  const C = 2 * Math.PI * 19;
  const ringDash = score > 0 ? `${(score / 100 * C).toFixed(2)} ${C.toFixed(2)}` : `0 ${C.toFixed(2)}`;

  const skills = (row.job?.required_skills ?? []).slice(0, 4);
  const title = row.job?.title ?? 'Unknown Role';
  const company = row.job?.company ?? '';
  const location = row.job?.location ?? '';

  const patchApi = useCallback(async (patch: Partial<Pick<SavedJob, 'status' | 'notes' | 'deadline'>>) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/saved-jobs/${row.job_hash}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      if (!res.ok) return;
      const updated = await res.json();
      onUpdate(updated);
    } catch {}
  }, [token, row.job_hash, onUpdate]);

  const cycleStatus = () => {
    const idx = STATUSES.findIndex(s => s.key === row.status);
    const next = STATUSES[(idx + 1) % STATUSES.length].key;
    setEmojiKey(k => k + 1);
    onUpdate({ ...row, status: next });
    patchApi({ status: next });
  };

  const scheduleNotesSave = (v: string) => {
    setSaveState('saving');
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      setSaveState('saved');
      patchApi({ notes: v });
    }, 750);
  };

  const handleNotesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value;
    setLocalNotes(v);
    scheduleNotesSave(v);
  };

  const insertTag = (tag: { emoji: string; label: string }) => {
    const snippet = `${tag.emoji} ${tag.label}  ·  `;
    const cur = localNotes;
    const next = cur ? (cur.replace(/\s*$/, '') + '\n' + snippet) : snippet;
    setLocalNotes(next);
    scheduleNotesSave(next);
  };

  const handleDeadlinePick = (iso: string) => {
    setDlOpen(false);
    onUpdate({ ...row, deadline: iso });
    patchApi({ deadline: iso });
  };

  const handleDeadlineClear = () => {
    setDlOpen(false);
    onUpdate({ ...row, deadline: null });
    patchApi({ deadline: '' });
  };

  return (
    <div className="sj-card-enter" style={{ position: 'relative', display: 'flex', background: '#1E293B', border: '1px solid rgba(148,163,184,0.15)', borderRadius: 16, zIndex: dlOpen ? 10 : 'auto' }}>
      {/* Status spine */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0, width: 4,
        background: sm.color, borderRadius: '16px 0 0 16px',
        boxShadow: `0 0 16px -2px ${hexA(sm.color, 0.6)}`,
        transition: 'background .4s ease, box-shadow .4s ease',
      }} />

      <div style={{ flex: 1, padding: '18px 20px 17px 24px', display: 'flex', flexDirection: 'column', gap: 13, minWidth: 0, position: 'relative' }}>

        {/* Header row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 14 }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 17, fontWeight: 600, color: '#F0F4FA', letterSpacing: '-0.01em' }}>{title}</div>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, marginTop: 5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              <span style={{ color: '#94A3B8' }}>{company}</span>
              {location && <span style={{ color: '#64748B' }}> · {location}</span>}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 'none' }}>
            {/* Status pill — click to cycle */}
            <button
              onClick={cycleStatus}
              title="Click to advance status"
              className="sj-pill"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 7, padding: '7px 11px',
                borderRadius: 10, background: hexA(sm.color, 0.14),
                border: `1px solid ${hexA(sm.color, 0.4)}`,
                color: '#E2E8F0', cursor: 'pointer', whiteSpace: 'nowrap',
                fontFamily: "'Source Sans 3',system-ui,sans-serif",
                transition: 'background .35s ease, border-color .35s ease',
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: sm.color, flex: 'none' }} />
              <span key={emojiKey} style={{ fontSize: 14, lineHeight: 1, display: 'inline-block', animation: emojiKey > 0 ? 'sjpop .42s cubic-bezier(.34,1.56,.64,1)' : 'none' }}>
                {sm.emoji}
              </span>
              <span style={{ fontWeight: 600, fontSize: 13 }}>{sm.label}</span>
              <span style={{ color: sm.color, fontSize: 13, marginLeft: 1, opacity: 0.7 }}>↻</span>
            </button>

            {/* Score ring */}
            {score > 0 && (
              <div style={{ position: 'relative', width: 46, height: 46, flex: 'none' }}>
                <svg width="46" height="46" viewBox="0 0 46 46" style={{ transform: 'rotate(-90deg)' }}>
                  <circle cx="23" cy="23" r="19" fill="none" stroke="rgba(148,163,184,0.16)" strokeWidth="3" />
                  <circle cx="23" cy="23" r="19" fill="none" stroke={rc} strokeWidth="3" strokeLinecap="round" strokeDasharray={ringDash} />
                </svg>
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Source Sans 3',system-ui,sans-serif", fontWeight: 700, fontSize: 12, color: rc, letterSpacing: '-0.02em' }}>
                  <span>{score}</span>
                  <span style={{ fontSize: 8, marginLeft: 1 }}>%</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Skills + deadline row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {skills.map(sk => (
              <span key={sk} style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, padding: '3px 9px', background: 'rgba(148,163,184,0.08)', color: '#94A3B8', borderRadius: 7, border: '1px solid rgba(148,163,184,0.12)' }}>
                {sk}
              </span>
            ))}
          </div>

          {/* Deadline badge */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setDlOpen(v => !v)}
              className="sj-dl-btn"
              style={dl ? {
                display: 'inline-flex', alignItems: 'center', gap: 8, height: 32, padding: '0 12px',
                borderRadius: 10, background: hexA(uc, 0.12), border: `1px solid ${hexA(uc, 0.32)}`,
                color: uc, fontWeight: 600, fontSize: 12.5, whiteSpace: 'nowrap', cursor: 'pointer',
                fontFamily: "'Source Sans 3',system-ui,sans-serif",
                transition: 'background .3s, border-color .3s, color .3s',
              } : {
                display: 'inline-flex', alignItems: 'center', gap: 7, height: 32, padding: '0 12px',
                borderRadius: 10, background: 'transparent', border: '1px dashed rgba(148,163,184,0.28)',
                color: '#94A3B8', fontWeight: 500, fontSize: 12.5, whiteSpace: 'nowrap', cursor: 'pointer',
                fontFamily: "'Source Sans 3',system-ui,sans-serif",
              }}
            >
              {dl ? (
                <>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: uc, flex: 'none', animation: 'sjblink 1.6s ease-in-out infinite' }} />
                  <span>{cd!.label}</span>
                </>
              ) : (
                <>
                  <span style={{ opacity: 0.85 }}>🗓</span>
                  <span>Set deadline</span>
                </>
              )}
            </button>

            {dlOpen && (
              <>
                <div onClick={() => setDlOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 20 }} />
                <CalPicker value={dl} onPick={handleDeadlinePick} onClear={handleDeadlineClear} />
              </>
            )}
          </div>
        </div>

        {/* Notes section */}
        <div style={{ marginTop: 2 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 16, marginBottom: 8 }}>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10.5, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#5E6B82' }}>Notes</div>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              fontFamily: "'JetBrains Mono',monospace", fontSize: 11,
              color: saveState === 'saved' ? '#34D399' : '#8AA8C8',
              opacity: saveState ? 1 : 0, transition: 'opacity .25s',
            }}>
              {saveState === 'saving' && (
                <span style={{ width: 11, height: 11, borderRadius: '50%', border: '1.6px solid currentColor', borderTopColor: 'transparent', animation: 'sjspin .6s linear infinite', display: 'inline-block' }} />
              )}
              <span>{saveState === 'saving' ? 'Saving…' : '✓ Saved'}</span>
            </div>
          </div>

          <div
            onClick={() => setNotesActive(true)}
            style={{
              position: 'relative', borderRadius: 12, overflow: 'hidden',
              background: notesActive ? '#141C2B' : '#131A28',
              border: `1px solid ${notesActive ? '#C2F45C' : '#28324A'}`,
              boxShadow: notesActive ? '0 0 0 3px rgba(194,244,92,0.14)' : 'none',
              maxHeight: notesActive ? 100 : 44,
              transition: 'max-height .28s cubic-bezier(.2,.8,.3,1), border-color .25s, background .25s, box-shadow .25s',
              cursor: 'text',
            }}
          >
            <textarea
              className="sj-notes-ta"
              onFocus={() => setNotesActive(true)}
              onBlur={() => { setTimeout(() => setNotesActive(false), 150); }}
              onChange={handleNotesChange}
              value={localNotes}
              placeholder="Recruiter name, application context, follow-up…"
              style={{
                display: 'block', width: '100%', boxSizing: 'border-box', resize: 'none',
                background: 'transparent', border: 'none', outline: 'none',
                color: '#DCE3EE', fontFamily: "'Source Sans 3',system-ui,sans-serif",
                fontSize: 13.5, lineHeight: 1.55, padding: '11px 13px', height: 100,
              }}
            />
          </div>

          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: 6, overflow: 'hidden', padding: '0 4px',
            maxHeight: notesActive ? 60 : 0, opacity: notesActive ? 1 : 0,
            marginTop: notesActive ? 8 : 0,
            transition: 'max-height .3s ease, opacity .25s ease, margin .3s ease',
          }}>
            {QUICK_TAGS.map(tag => (
              <button
                key={tag.label}
                onMouseDown={e => e.preventDefault()}
                onClick={() => insertTag(tag)}
                className="sj-tag-btn"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6, height: 27, padding: '0 10px',
                  borderRadius: 8, background: '#1B2435', border: '1px solid #2C3852',
                  color: '#AEB9CC', fontSize: 11.5, fontWeight: 500, cursor: 'pointer',
                  transition: 'transform .12s, background .15s, color .15s, border-color .15s',
                }}
              >
                <span style={{ fontSize: 13, lineHeight: 1 }}>{tag.emoji}</span>
                <span>{tag.label}</span>
                <span style={{ color: '#C2F45C', fontWeight: 700, marginLeft: -1 }}>+</span>
              </button>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

const SavedJobsPage: React.FC = () => {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [token, setToken] = useState<string | null>(null);
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<'all' | SavedJobStatus>('all');

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const authToken = await getToken();
        setToken(authToken);
        const res = await fetch(`${API_BASE_URL}/api/saved-jobs`, {
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
        });
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        const data = await res.json();
        setSavedJobs(Array.isArray(data) ? data : []);
      } catch (e: any) {
        setError(e.message || 'Failed to load saved jobs.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [isLoaded, isSignedIn, getToken]);

  const handleUpdate = useCallback((updated: SavedJob) => {
    setSavedJobs(prev => prev.map(j => j.job_hash === updated.job_hash ? updated : j));
  }, []);

  const filteredJobs = useMemo(() => {
    if (filter === 'all') return savedJobs;
    return savedJobs.filter(j => j.status === filter);
  }, [savedJobs, filter]);

  const counts = useMemo(() => {
    const map: Record<string, number> = { all: savedJobs.length };
    STATUSES.forEach(s => { map[s.key] = savedJobs.filter(j => j.status === s.key).length; });
    return map;
  }, [savedJobs]);

  if (!isLoaded) {
    return (
      <div style={{ minHeight: '100vh', background: '#0F172A' }}>
        <Header />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 256 }}>
          <div style={{ width: 32, height: 32, borderRadius: '50%', border: '2px solid #E2E8F0', borderTopColor: 'transparent', animation: 'sjspin .8s linear infinite' }} />
        </div>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div style={{ minHeight: '100vh', background: '#0F172A', fontFamily: "'Source Sans 3',system-ui,sans-serif" }}>
        <style>{TRACKER_CSS}</style>
        <Header />
        <main style={{ maxWidth: 760, margin: '0 auto', padding: '96px 24px' }}>
          <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 32, marginBottom: 24, opacity: 0.4 }}>🔖</div>
          <h1 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: 36, color: '#E2E8F0', marginBottom: 12 }}>Save jobs as you compare them.</h1>
          <p style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: '#64748B', marginBottom: 32, maxWidth: 360 }}>
            Sign in to keep a private application tracker across analyses.
          </p>
          <SignInButton mode="modal">
            <button style={{ display: 'inline-block', background: '#E2E8F0', color: '#0F172A', padding: '10px 20px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, letterSpacing: '0.08em', cursor: 'pointer', border: 'none', borderRadius: 8 }}>
              Sign in →
            </button>
          </SignInButton>
        </main>
      </div>
    );
  }

  return (
    <>
      <style>{TRACKER_CSS}</style>
      <div style={{ minHeight: '100vh', background: '#0F172A', fontFamily: "'Source Sans 3',system-ui,sans-serif", WebkitFontSmoothing: 'antialiased' }}>
        <Header />

        <div style={{ maxWidth: 760, margin: '0 auto', padding: '40px 24px 96px', position: 'relative', zIndex: 1 }}>

          {/* Page header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#64748B' }}>
            <span style={{ width: 18, height: 1, background: 'rgba(148,163,184,0.45)', display: 'inline-block' }} />
            Application Tracker
          </div>
          <h1 style={{ fontFamily: "'Instrument Serif','Source Serif 4',Georgia,serif", fontWeight: 600, fontSize: 44, lineHeight: 1.04, color: '#E2E8F0', margin: '12px 0 10px', letterSpacing: '-0.015em' }}>
            Saved jobs.
          </h1>
          <p style={{ fontSize: 16, color: '#94A3B8', margin: '0 0 26px' }}>
            Track status, notes, and deadlines for roles you want to pursue.
          </p>

          {/* Filter tabs */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, paddingBottom: 22, borderBottom: '1px solid rgba(148,163,184,0.12)' }}>
            <button
              onClick={() => setFilter('all')}
              className="sj-filter-tab"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 13px',
                borderRadius: 10, cursor: 'pointer',
                background: filter === 'all' ? '#1E293B' : 'transparent',
                border: `1px solid ${filter === 'all' ? 'rgba(148,163,184,0.18)' : 'rgba(148,163,184,0.12)'}`,
                fontSize: 13, fontWeight: filter === 'all' ? 500 : 400,
                color: filter === 'all' ? '#E2E8F0' : '#64748B',
                fontFamily: "'Source Sans 3',system-ui,sans-serif",
              }}
            >
              All
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: '#64748B' }}>{counts.all}</span>
            </button>

            {STATUSES.map(s => (
              <button
                key={s.key}
                onClick={() => setFilter(s.key)}
                className="sj-filter-tab"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 13px',
                  borderRadius: 10, cursor: 'pointer',
                  background: filter === s.key ? '#1E293B' : 'transparent',
                  border: `1px solid ${filter === s.key ? 'rgba(148,163,184,0.18)' : 'rgba(148,163,184,0.12)'}`,
                  fontSize: 13, fontWeight: filter === s.key ? 500 : 400,
                  color: filter === s.key ? '#E2E8F0' : '#94A3B8',
                  fontFamily: "'Source Sans 3',system-ui,sans-serif",
                }}
              >
                {s.emoji} {s.label}
                <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, padding: '1px 6px', borderRadius: 6, background: 'rgba(148,163,184,0.08)', color: '#64748B' }}>
                  {counts[s.key] ?? 0}
                </span>
              </button>
            ))}
          </div>

          {/* Loading */}
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 160 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', border: '2px solid #334155', borderTopColor: '#94A3B8', animation: 'sjspin .8s linear infinite' }} />
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div style={{ border: '1px solid rgba(251,113,133,0.3)', background: 'rgba(251,113,133,0.06)', padding: '14px 18px', borderRadius: 12, marginTop: 22 }}>
              <p style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: '#FB7185', margin: 0 }}>{error}</p>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && savedJobs.length === 0 && (
            <div style={{ paddingTop: 80 }}>
              <div style={{ fontSize: 32, marginBottom: 20, opacity: 0.35 }}>📋</div>
              <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: 28, color: '#E2E8F0', marginBottom: 8 }}>No saved jobs yet.</h2>
              <p style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: '#64748B', marginBottom: 32, maxWidth: 400 }}>
                Run a match, save the roles you care about, then manage your application list here.
              </p>
              <Link
                to="/find"
                style={{ display: 'inline-block', background: '#E2E8F0', color: '#0F172A', padding: '10px 20px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, letterSpacing: '0.08em', borderRadius: 8, textDecoration: 'none' }}
              >
                Find matches →
              </Link>
            </div>
          )}

          {/* Cards */}
          {!loading && savedJobs.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 22 }}>
              {filteredJobs.length === 0 ? (
                <div style={{ padding: '64px 0', textAlign: 'center' }}>
                  <p style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: '#475569' }}>
                    No jobs in this status.
                  </p>
                </div>
              ) : (
                filteredJobs.map(row => (
                  <TrackerCard key={row.job_hash} row={row} token={token} onUpdate={handleUpdate} />
                ))
              )}
            </div>
          )}

        </div>
      </div>
    </>
  );
};

export default SavedJobsPage;
