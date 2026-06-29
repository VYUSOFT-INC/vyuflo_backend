// src/components/layout/Publiclayot.tsx
import type { ReactNode } from 'react';
import { Globe } from 'lucide-react';

interface PublicLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

export default function PublicLayout({ children, title, subtitle }: PublicLayoutProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 flex">
      {/* Left branding panel */}
      <div className="hidden lg:flex lg:w-[45%] bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-800 flex-col justify-between p-12 relative overflow-hidden">
        {/* Decorative blobs */}
        <div className="absolute -top-32 -right-32 w-96 h-96 bg-white/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-violet-500/20 rounded-full blur-3xl" />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
            <Globe className="w-6 h-6 text-white" />
          </div>
          <span className="text-white font-bold text-xl tracking-tight">ImmigrationPro</span>
        </div>

        {/* Headline */}
        <div className="relative z-10">
          <h2 className="text-white text-4xl font-bold leading-tight mb-5">
            Navigate your immigration journey with confidence
          </h2>
          <p className="text-indigo-200 text-lg leading-relaxed mb-10">
            Expert guidance, streamlined case management, and real-time status updates — all in one secure platform.
          </p>

          {/* Feature list */}
          <ul className="space-y-4">
            {[
              { icon: '⚡', text: 'Real-time case status tracking' },
              { icon: '🔒', text: 'Bank-grade document security' },
              { icon: '🤝', text: 'Direct attorney communication' },
              { icon: '📰', text: 'Immigration news & policy updates' },
            ].map(({ icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-indigo-100">
                <span className="text-xl w-8">{icon}</span>
                <span className="text-sm">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Trust badges */}
        <div className="relative z-10 flex gap-4">
          {['SOC 2 Certified', 'HIPAA Compliant', 'ITAR Registered'].map((badge) => (
            <span
              key={badge}
              className="px-3 py-1.5 text-xs font-medium text-indigo-200 border border-indigo-400/40 rounded-full bg-white/5"
            >
              {badge}
            </span>
          ))}
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 lg:px-12 xl:px-16">
        {/* Mobile logo */}
        <div className="lg:hidden flex items-center gap-2.5 mb-10">
          <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center">
            <Globe className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-gray-900 text-xl">ImmigrationPro</span>
        </div>

        <div className="w-full max-w-md">
          {(title ?? subtitle) && (
            <div className="mb-8">
              {title && <h1 className="text-2xl font-bold text-gray-900">{title}</h1>}
              {subtitle && <p className="mt-2 text-gray-500 text-sm leading-relaxed">{subtitle}</p>}
            </div>
          )}
          {children}
        </div>
      </div>
    </div>
  );
}
