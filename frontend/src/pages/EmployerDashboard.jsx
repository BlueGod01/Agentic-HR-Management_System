import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { employerAPI } from '../services/api'
import useAuthStore from '../store/authStore'
import {
  AlertTriangle, Mail, Users, MessageSquare, LogOut,
  Bot, RefreshCw, Send, Check, X, Loader2, Bell,
  ChevronDown, Shield, TrendingUp
} from 'lucide-react'

const TABS = ['Alerts', 'Email Drafts', 'Employees', 'WhatsApp']

export default function EmployerDashboard() {
  const [activeTab, setActiveTab] = useState('Alerts')
  const [alerts, setAlerts] = useState({ total: 0, high_severity: 0, by_type: {}, alerts: [] })
  const [summary, setSummary] = useState('')
  const [drafts, setDrafts] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(false)
  const [waMessage, setWaMessage] = useState('')
  const [waSending, setWaSending] = useState(false)
  const [emailForm, setEmailForm] = useState({ recipient_email: '', recipient_name: '', subject_hint: '', body_instruction: '' })
  const [generating, setGenerating] = useState(false)
  const { logout } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    loadAlerts()
    loadDrafts()
    loadEmployees()
  }, [])

  const loadAlerts = async () => {
    setLoading(true)
    try {
      const [alertRes, summaryRes] = await Promise.all([
        employerAPI.getAlerts({ hours: 24 }),
        employerAPI.getAlertSummary(24),
      ])
      setAlerts(alertRes.data)
      setSummary(summaryRes.data.summary)
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  const loadDrafts = async () => {
    try { const r = await employerAPI.listDrafts(); setDrafts(r.data) } catch (e) {}
  }

  const loadEmployees = async () => {
    try { const r = await employerAPI.listEmployees({}); setEmployees(r.data) } catch (e) {}
  }

  const generateEmail = async () => {
    setGenerating(true)
    try {
      await employerAPI.generateEmail(emailForm)
      await loadDrafts()
      setEmailForm({ recipient_email: '', recipient_name: '', subject_hint: '', body_instruction: '' })
      setActiveTab('Email Drafts')
    } catch (e) { alert('Failed to generate email') }
    setGenerating(false)
  }

  const approveDraft = async (id, action) => {
    try {
      await employerAPI.approveEmail({ draft_id: id, action })
      await loadDrafts()
    } catch (e) { alert('Action failed') }
  }

  const sendWhatsApp = async () => {
    if (!waMessage.trim()) return
    setWaSending(true)
    try {
      await employerAPI.sendWhatsApp(waMessage)
      setWaMessage('')
      alert('Message sent!')
    } catch (e) { alert('Failed to send') }
    setWaSending(false)
  }

  const handleLogout = () => { logout(); navigate('/login') }

  const severityBadge = (s) => {
    const map = { high: 'badge-high', critical: 'badge-high', medium: 'badge-medium', low: 'badge-low' }
    return <span className={map[s] || 'badge-low'}>{s}</span>
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-brand-900 text-white flex flex-col shrink-0">
        <div className="p-5 border-b border-brand-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <p className="font-semibold text-sm">Employer Panel</p>
              <p className="text-brand-300 text-xs">HR Control Centre</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {[
            { name: 'Alerts', icon: Bell },
            { name: 'Email Drafts', icon: Mail },
            { name: 'Employees', icon: Users },
            { name: 'WhatsApp', icon: MessageSquare },
          ].map(({ name, icon: Icon }) => (
            <button
              key={name}
              onClick={() => setActiveTab(name)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                activeTab === name ? 'bg-brand-600 text-white' : 'text-brand-300 hover:bg-brand-800 hover:text-white'
              }`}
            >
              <Icon className="w-4 h-4" />
              {name}
            </button>
          ))}
        </nav>

        {/* Stats */}
        <div className="p-3 space-y-2 border-t border-brand-800">
          <div className="bg-brand-800 rounded-xl p-3 grid grid-cols-2 gap-2 text-center">
            <div>
              <p className="text-xl font-bold text-red-400">{alerts.high_severity}</p>
              <p className="text-brand-400 text-xs">High Alerts</p>
            </div>
            <div>
              <p className="text-xl font-bold">{alerts.total}</p>
              <p className="text-brand-400 text-xs">Total (24h)</p>
            </div>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-2 text-brand-300 hover:text-white w-full px-3 py-2 rounded-lg hover:bg-brand-800 transition-colors text-sm">
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6">

          {/* ── Alerts Tab ── */}
          {activeTab === 'Alerts' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-800">Security Alerts (Last 24h)</h2>
                <button onClick={loadAlerts} className="btn-secondary flex items-center gap-2 text-sm">
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
                </button>
              </div>

              {/* Summary card */}
              {summary && (
                <div className="card mb-6 bg-gradient-to-br from-brand-50 to-blue-50 border-brand-100">
                  <div className="flex items-center gap-2 mb-3">
                    <Bot className="w-5 h-5 text-brand-600" />
                    <h3 className="font-semibold text-brand-800">AI Summary</h3>
                  </div>
                  <p className="text-sm text-gray-700 whitespace-pre-line">{summary}</p>
                </div>
              )}

              {/* Alert list */}
              {alerts.alerts.length === 0 ? (
                <div className="card text-center py-12">
                  <Shield className="w-12 h-12 text-green-400 mx-auto mb-3" />
                  <p className="font-medium text-gray-600">No alerts in the last 24 hours</p>
                  <p className="text-sm text-gray-400">All clear!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {alerts.alerts.map((a) => (
                    <div key={a.id} className="card hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              {severityBadge(a.severity)}
                              <span className="text-xs text-gray-400">{a.violation_type?.replace(/_/g, ' ')}</span>
                            </div>
                            <p className="text-sm text-gray-700">{a.description}</p>
                            <p className="text-xs text-gray-400 mt-1">User #{a.user_id} · {new Date(a.created_at).toLocaleString()}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Email Drafts Tab ── */}
          {activeTab === 'Email Drafts' && (
            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-6">Email Management</h2>

              {/* Generate form */}
              <div className="card mb-6">
                <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Bot className="w-4 h-4 text-brand-600" /> Generate AI Email Draft
                </h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Recipient Email</label>
                    <input className="input" placeholder="employee@company.com" value={emailForm.recipient_email} onChange={e => setEmailForm(f => ({ ...f, recipient_email: e.target.value }))} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Recipient Name</label>
                    <input className="input" placeholder="Alice Johnson" value={emailForm.recipient_name} onChange={e => setEmailForm(f => ({ ...f, recipient_name: e.target.value }))} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Subject Hint</label>
                    <input className="input" placeholder="Leave approval notification" value={emailForm.subject_hint} onChange={e => setEmailForm(f => ({ ...f, subject_hint: e.target.value }))} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Body Instruction</label>
                    <input className="input" placeholder="Inform the employee their leave was approved" value={emailForm.body_instruction} onChange={e => setEmailForm(f => ({ ...f, body_instruction: e.target.value }))} />
                  </div>
                </div>
                <button onClick={generateEmail} disabled={generating || !emailForm.recipient_email} className="btn-primary flex items-center gap-2 text-sm">
                  {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                  {generating ? 'Generating…' : 'Generate Draft'}
                </button>
              </div>

              {/* Drafts list */}
              <div className="space-y-4">
                {drafts.map(d => (
                  <div key={d.id} className="card">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <p className="font-medium text-gray-800">{d.subject}</p>
                        <p className="text-xs text-gray-400">To: {d.recipient_email} · {d.status}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${d.status === 'sent' ? 'bg-green-100 text-green-700' : d.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {d.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 whitespace-pre-line mb-4 max-h-32 overflow-y-auto bg-gray-50 rounded p-3">{d.body}</p>
                    {d.status === 'pending_approval' && (
                      <div className="flex gap-2">
                        <button onClick={() => approveDraft(d.id, 'approve')} className="btn-primary text-sm flex items-center gap-1 py-1.5">
                          <Check className="w-3 h-3" /> Approve & Send
                        </button>
                        <button onClick={() => approveDraft(d.id, 'reject')} className="btn-secondary text-sm flex items-center gap-1 py-1.5 text-red-600 border-red-200">
                          <X className="w-3 h-3" /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                ))}
                {drafts.length === 0 && (
                  <div className="card text-center py-10 text-gray-400">
                    <Mail className="w-10 h-10 mx-auto mb-2 opacity-40" />
                    <p>No email drafts yet. Generate one above.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Employees Tab ── */}
          {activeTab === 'Employees' && (
            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-6">Employee Directory</h2>
              <div className="card overflow-hidden p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-100">
                      <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Employee</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Department</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Designation</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {employees.map(e => (
                      <tr key={e.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center text-brand-700 font-bold text-xs">
                              {e.full_name.charAt(0)}
                            </div>
                            <div>
                              <p className="font-medium text-gray-800">{e.full_name}</p>
                              <p className="text-gray-400 text-xs">{e.employee_code}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-600">{e.department}</td>
                        <td className="px-4 py-3 text-gray-600">{e.designation}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${e.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                            {e.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {employees.length === 0 && (
                  <div className="text-center py-10 text-gray-400">
                    <Users className="w-10 h-10 mx-auto mb-2 opacity-40" />
                    <p>No employees found</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── WhatsApp Tab ── */}
          {activeTab === 'WhatsApp' && (
            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-6">WhatsApp Notifications</h2>
              <div className="card max-w-xl">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">Send to Employer</p>
                    <p className="text-xs text-gray-400">Message will be sent to the configured employer number</p>
                  </div>
                </div>
                <textarea
                  className="input mt-4 resize-none"
                  rows={5}
                  placeholder="Type your message…"
                  value={waMessage}
                  onChange={e => setWaMessage(e.target.value)}
                />
                <button
                  onClick={sendWhatsApp}
                  disabled={waSending || !waMessage.trim()}
                  className="btn-primary mt-3 flex items-center gap-2 text-sm"
                >
                  {waSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  {waSending ? 'Sending…' : 'Send WhatsApp'}
                </button>

                <div className="mt-6 pt-4 border-t border-gray-100">
                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Quick Messages</h4>
                  <div className="space-y-2">
                    {['alerts', 'Send daily summary to my WhatsApp'].map((msg, i) => (
                      <button
                        key={i}
                        onClick={() => setWaMessage(msg)}
                        className="w-full text-left text-sm text-brand-600 hover:text-brand-800 bg-brand-50 hover:bg-brand-100 rounded-lg px-3 py-2 transition-colors"
                      >
                        {msg}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  )
}
