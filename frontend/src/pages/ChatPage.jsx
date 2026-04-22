import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { chatAPI, employeeAPI } from '../services/api'
import useAuthStore from '../store/authStore'
import {
  Bot, Send, LogOut, User, Wallet, Calendar, FileText,
  Plus, AlertTriangle, Loader2, ChevronRight
} from 'lucide-react'

const SUGGESTED = [
  "What is my current salary breakdown?",
  "How many leave days do I have left?",
  "What is the work from home policy?",
  "Can I apply for 3 days of leave next week?",
  "What is the annual leave policy?",
]

function generateSessionId() {
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sessionId] = useState(generateSessionId)
  const [isTyping, setIsTyping] = useState(false)
  const [profile, setProfile] = useState(null)
  const [leaveBalance, setLeaveBalance] = useState(null)
  const bottomRef = useRef(null)
  const { logout } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  useEffect(() => {
    employeeAPI.getProfile().then(r => setProfile(r.data)).catch(() => {})
    employeeAPI.getLeaveBalance().then(r => setLeaveBalance(r.data)).catch(() => {})

    // Welcome message
    setMessages([{
      role: 'assistant',
      content: "Hello! 👋 I'm your AI HR assistant. I can help you with your salary details, leave balance, company policies, and more. How can I help you today?",
      id: 'welcome',
    }])
  }, [])

  const sendMessage = async (text) => {
    const userText = text || input.trim()
    if (!userText) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userText, id: Date.now() }])
    setIsTyping(true)

    try {
      const { data } = await chatAPI.sendMessage(userText, sessionId)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        id: Date.now() + 1,
        violation: data.violation_detected,
        tool: data.tool_used,
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again.",
        id: Date.now() + 1,
        isError: true,
      }])
    } finally {
      setIsTyping(false)
    }
  }

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-72 bg-brand-900 text-white flex flex-col shrink-0">
        {/* Logo */}
        <div className="p-5 border-b border-brand-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <p className="font-semibold text-sm">HR Assistant</p>
              <p className="text-brand-300 text-xs">Gemini AI Powered</p>
            </div>
          </div>
        </div>

        {/* Profile card */}
        {profile && (
          <div className="p-4 m-3 bg-brand-800 rounded-xl">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-brand-600 rounded-full flex items-center justify-center text-sm font-bold">
                {profile.full_name.charAt(0)}
              </div>
              <div>
                <p className="font-medium text-sm">{profile.full_name}</p>
                <p className="text-brand-300 text-xs">{profile.designation}</p>
              </div>
            </div>
            <div className="text-xs text-brand-300">{profile.department}</div>
          </div>
        )}

        {/* Quick stats */}
        {leaveBalance && (
          <div className="px-3 mb-2">
            <p className="text-brand-400 text-xs uppercase tracking-wide mb-2 px-1">Leave Balance</p>
            <div className="bg-brand-800 rounded-xl p-3 grid grid-cols-3 gap-2 text-center">
              <div>
                <p className="text-lg font-bold">{leaveBalance.total_leave_days}</p>
                <p className="text-brand-400 text-xs">Total</p>
              </div>
              <div>
                <p className="text-lg font-bold text-yellow-400">{leaveBalance.used_leave_days}</p>
                <p className="text-brand-400 text-xs">Used</p>
              </div>
              <div>
                <p className="text-lg font-bold text-green-400">{leaveBalance.remaining_leave}</p>
                <p className="text-brand-400 text-xs">Left</p>
              </div>
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="px-3 flex-1">
          <p className="text-brand-400 text-xs uppercase tracking-wide mb-2 px-1 mt-2">Quick Ask</p>
          <div className="space-y-1">
            {SUGGESTED.map((s, i) => (
              <button
                key={i}
                onClick={() => sendMessage(s)}
                className="w-full text-left text-xs text-brand-200 hover:text-white hover:bg-brand-700 px-3 py-2 rounded-lg transition-colors flex items-center gap-2 group"
              >
                <ChevronRight className="w-3 h-3 text-brand-500 group-hover:text-brand-300 shrink-0" />
                <span className="line-clamp-2">{s}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Logout */}
        <div className="p-3 border-t border-brand-800">
          <button onClick={handleLogout} className="flex items-center gap-2 text-brand-300 hover:text-white w-full px-3 py-2 rounded-lg hover:bg-brand-800 transition-colors text-sm">
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Chat area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-gray-800">HR Chat Assistant</h1>
            <p className="text-xs text-gray-400">Your personal HR queries answered instantly</p>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
            <span className="text-xs text-gray-500">Online</span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-brand-600" />
                </div>
              )}
              <div className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
                {msg.violation && (
                  <div className="flex items-center gap-1 text-amber-600 text-xs mb-1">
                    <AlertTriangle className="w-3 h-3" />
                    <span>Security event logged</span>
                  </div>
                )}
                <div className="text-sm prose prose-sm max-w-none">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
                {msg.tool && (
                  <p className="text-xs mt-1 opacity-50">Used: {msg.tool}</p>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center shrink-0 mt-1">
                  <User className="w-4 h-4 text-gray-500" />
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-brand-600" />
              </div>
              <div className="chat-bubble-ai flex items-center gap-1 py-3">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="bg-white border-t border-gray-100 px-6 py-4">
          <div className="flex gap-3 items-end">
            <textarea
              className="input flex-1 resize-none min-h-[44px] max-h-32 py-2.5"
              placeholder="Ask about your salary, leave, policies…"
              value={input}
              rows={1}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage()
                }
              }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isTyping}
              className="btn-primary px-4 py-2.5 flex items-center gap-2"
            >
              {isTyping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1.5">Press Enter to send, Shift+Enter for new line</p>
        </div>
      </main>
    </div>
  )
}
