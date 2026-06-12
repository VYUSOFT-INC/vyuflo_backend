// import { useState, type ReactNode } from 'react';
// import { Search, ChevronDown, ChevronUp, CheckCircle, Circle, BookOpen, Target, Lightbulb, Clock } from 'lucide-react';
// import EmployeeLayout from '../../components/layout/EmployeeLayout';

// function Card({ children, className = '', padding = 'md' }: { children: ReactNode; className?: string; padding?: 'none' | 'sm' | 'md' | 'lg' }) {
//   const p = { none: '', sm: 'p-4', md: 'p-6', lg: 'p-8' };
//   return <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${p[padding]} ${className}`}>{children}</div>;
// }

// type Difficulty = 'easy' | 'medium' | 'hard';
// interface Question { id: string; question: string; answer: string; difficulty: Difficulty; done: boolean; }
// interface Category { id: string; label: string; icon: ReactNode; count: number; questions: Question[]; }

// const CATEGORIES: Category[] = [
//   {
//     id: 'basics', label: 'H-1B Basics', icon: <BookOpen size={16} />, count: 4,
//     questions: [
//       { id: 'q1', question: 'What is the H-1B visa and who qualifies?', difficulty: 'easy', done: false, answer: 'The H-1B visa is a non-immigrant work visa that allows U.S. employers to hire foreign workers in specialty occupations requiring at least a bachelor\'s degree or equivalent. Qualifying occupations include IT, engineering, finance, accounting, architecture, law, and medicine.' },
//       { id: 'q2', question: 'What documents are required for H-1B filing?', difficulty: 'easy', done: false, answer: 'Key documents include: passport, academic transcripts and degree certificates, resume/CV, job offer letter, LCA (Labor Condition Application) approval, Form I-129, and specialty occupation evidence.' },
//       { id: 'q3', question: 'What is the H-1B cap and lottery process?', difficulty: 'medium', done: false, answer: 'The annual H-1B cap is 65,000 visas (plus 20,000 for US master\'s degree holders). When petitions exceed the cap, USCIS conducts a computer-based random lottery. Registration occurs in March for the following fiscal year starting October 1.' },
//       { id: 'q4', question: 'Can I work for multiple employers on H-1B?', difficulty: 'medium', done: false, answer: 'Yes, through H-1B concurrent employment. Each employer must file a separate H-1B petition. The second employer\'s petition can be filed and you can begin working once it\'s received (for cap-exempt concurrent employment) or approved.' },
//     ],
//   },
//   {
//     id: 'interview', label: 'Visa Interview', icon: <Target size={16} />, count: 4,
//     questions: [
//       { id: 'q5', question: 'What should I bring to the visa interview?', difficulty: 'easy', done: false, answer: 'Bring: DS-160 confirmation, appointment confirmation, valid passport, photo, visa fee receipt, I-797 approval notice, employment letter, pay stubs, tax returns, and any supporting documents for your visa category.' },
//       { id: 'q6', question: 'What questions are typically asked at the consulate?', difficulty: 'medium', done: false, answer: 'Common questions: What is your job title and duties? Who is your employer? What is your salary? How long have you worked there? What are your qualifications? Do you intend to immigrate permanently? Do you have ties to your home country?' },
//       { id: 'q7', question: 'What are common reasons for visa denial?', difficulty: 'medium', done: false, answer: 'Common denial reasons include: insufficient ties to home country, immigrant intent (214b), missing documents, misrepresentation, prior immigration violations, ineligibility under specific visa rules, and consular officer discretion.' },
//       { id: 'q8', question: 'How should I explain gaps in employment?', difficulty: 'hard', done: false, answer: 'Be honest and straightforward. Provide documentation if available (school enrollment, medical records, freelance contracts). Frame gaps positively — skill development, caregiving, education, or personal challenges. Consistency between your DS-160 and verbal answers is critical.' },
//     ],
//   },
//   {
//     id: 'gc', label: 'Green Card Path', icon: <Target size={16} />, count: 3,
//     questions: [
//       { id: 'q9', question: 'What are the EB-1, EB-2, and EB-3 preference categories?', difficulty: 'medium', done: false, answer: 'EB-1: Priority workers (extraordinary ability, outstanding professors, multinational managers). EB-2: Advanced degree professionals or exceptional ability. EB-3: Skilled workers, professionals, and unskilled workers. Each has different requirements and wait times based on country of birth.' },
//       { id: 'q10', question: 'What is PERM labor certification?', difficulty: 'hard', done: false, answer: 'PERM (Program Electronic Review Management) is the first step for EB-2 and EB-3 green cards. The employer must prove no qualified US workers are available by conducting recruitment (ads, job postings). DOL must certify the application before I-140 filing.' },
//       { id: 'q11', question: 'How does priority date affect green card timing?', difficulty: 'hard', done: false, answer: 'Priority date is when your I-140 or PERM was filed. Visa availability depends on your preference category and country of birth. The Visa Bulletin monthly updates show "current" dates — when your priority date is on or before the listed date, you can file I-485 or schedule consular processing.' },
//     ],
//   },
//   {
//     id: 'opt', label: 'OPT & STEM OPT', icon: <Lightbulb size={16} />, count: 3,
//     questions: [
//       { id: 'q12', question: 'What is the difference between OPT and CPT?', difficulty: 'easy', done: false, answer: 'CPT (Curricular Practical Training) is authorized before graduation and must be integral to your degree. OPT (Optional Practical Training) is post-graduation work authorization. CPT used for 12+ months may affect OPT eligibility. OPT provides 12 months (36 months with STEM extension).' },
//       { id: 'q13', question: 'How do I apply for STEM OPT extension?', difficulty: 'medium', done: false, answer: 'Requirements: STEM degree, employer enrolled in E-Verify, Form I-983 training plan. Apply 90 days before OPT expires. Your DSO endorses Form I-20, you file I-765 with USCIS. Approval extends work authorization by 24 months (total 36 months OPT).' },
//       { id: 'q14', question: 'What happens if my OPT application is pending?', difficulty: 'medium', done: false, answer: 'If filed on time (at least 90 days before expiration), a 180-day cap-gap protection applies for F-1 students. You can continue working during the 180-day cap-gap if you\'re in valid F-1 status and your employer maintains your record in E-Verify.' },
//     ],
//   },
// ];

// const DIFF_STYLES: Record<Difficulty, string> = {
//   easy: 'bg-emerald-50 text-emerald-700',
//   medium: 'bg-amber-50 text-amber-700',
//   hard: 'bg-red-50 text-red-700',
// };

// export default function InterviewPrep() {
//   const [search, setSearch] = useState('');
//   const [activeCategory, setActiveCategory] = useState('basics');
//   const [expandedId, setExpandedId] = useState<string | null>(null);
//   const [questions, setQuestions] = useState<Record<string, Question[]>>(
//     Object.fromEntries(CATEGORIES.map((c) => [c.id, c.questions]))
//   );

//   const toggleDone = (categoryId: string, qId: string) => {
//     setQuestions((prev) => ({
//       ...prev,
//       [categoryId]: prev[categoryId].map((q) => q.id === qId ? { ...q, done: !q.done } : q),
//     }));
//   };

//   const activeCat = CATEGORIES.find((c) => c.id === activeCategory)!;
//   const activeQuestions = questions[activeCategory] ?? [];
//   const filteredQuestions = search
//     ? Object.values(questions).flat().filter((q) => q.question.toLowerCase().includes(search.toLowerCase()))
//     : activeQuestions;

//   const totalDone = Object.values(questions).flat().filter((q) => q.done).length;
//   const totalQuestions = Object.values(questions).flat().length;

//   return (
//     <EmployeeLayout>
//       <div className="space-y-6">
//         {/* Header */}
//         <div>
//           <h1 className="text-2xl font-bold text-gray-900">Interview Preparation</h1>
//           <p className="text-sm text-gray-500 mt-0.5">Practice common immigration questions to prepare for your visa interview</p>
//         </div>

//         {/* Progress summary */}
//         <Card padding="sm">
//           <div className="flex items-center gap-6">
//             <div className="flex items-center gap-3">
//               <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center">
//                 <Target size={18} className="text-indigo-600" />
//               </div>
//               <div>
//                 <p className="text-2xl font-bold text-gray-900">{totalDone}/{totalQuestions}</p>
//                 <p className="text-xs text-gray-500">Questions Reviewed</p>
//               </div>
//             </div>
//             <div className="flex-1">
//               <div className="flex justify-between text-xs text-gray-500 mb-1.5">
//                 <span>Overall Progress</span>
//                 <span className="font-semibold text-gray-700">{Math.round((totalDone / totalQuestions) * 100)}%</span>
//               </div>
//               <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
//                 <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
//                   style={{ width: `${(totalDone / totalQuestions) * 100}%` }} />
//               </div>
//             </div>
//             <div className="flex items-center gap-2 text-xs text-gray-500">
//               <Clock size={14} />
//               <span>~{Math.ceil((totalQuestions - totalDone) * 3)} min remaining</span>
//             </div>
//           </div>
//         </Card>

//         {/* Search */}
//         <div className="relative">
//           <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
//           <input
//             type="text"
//             placeholder="Search questions..."
//             value={search}
//             onChange={(e) => setSearch(e.target.value)}
//             className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
//           />
//         </div>

//         {search ? (
//           /* Search results */
//           <Card padding="none">
//             <div className="px-5 py-3 border-b border-gray-100">
//               <p className="text-sm font-medium text-gray-700">{filteredQuestions.length} result{filteredQuestions.length !== 1 ? 's' : ''} for "{search}"</p>
//             </div>
//             <ul className="divide-y divide-gray-50">
//               {filteredQuestions.map((q) => {
//                 const catId = CATEGORIES.find((c) => c.questions.some((cq) => cq.id === q.id))?.id ?? activeCategory;
//                 return <QuestionItem key={q.id} q={q} expanded={expandedId === q.id} onExpand={() => setExpandedId(expandedId === q.id ? null : q.id)} onToggle={() => toggleDone(catId, q.id)} />;
//               })}
//             </ul>
//           </Card>
//         ) : (
//           <div className="flex flex-col lg:flex-row gap-4">
//             {/* Category sidebar */}
//             <div className="lg:w-56 shrink-0">
//               <Card padding="none">
//                 <div className="px-4 py-3 border-b border-gray-100">
//                   <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Topics</p>
//                 </div>
//                 <ul className="p-2 space-y-1">
//                   {CATEGORIES.map((cat) => {
//                     const catDone = (questions[cat.id] ?? []).filter((q) => q.done).length;
//                     return (
//                       <li key={cat.id}>
//                         <button
//                           onClick={() => setActiveCategory(cat.id)}
//                           className={['w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left',
//                             activeCategory === cat.id ? 'bg-indigo-50 text-indigo-700' : 'text-gray-700 hover:bg-gray-50'].join(' ')}
//                         >
//                           <span className="flex items-center gap-2">
//                             <span className={activeCategory === cat.id ? 'text-indigo-600' : 'text-gray-400'}>{cat.icon}</span>
//                             {cat.label}
//                           </span>
//                           <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${catDone === cat.count ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
//                             {catDone}/{cat.count}
//                           </span>
//                         </button>
//                       </li>
//                     );
//                   })}
//                 </ul>
//               </Card>
//             </div>

//             {/* Questions */}
//             <div className="flex-1 min-w-0">
//               <Card padding="none">
//                 <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
//                   <div>
//                     <h2 className="text-base font-semibold text-gray-900">{activeCat.label}</h2>
//                     <p className="text-xs text-gray-500 mt-0.5">
//                       {activeQuestions.filter((q) => q.done).length} of {activeQuestions.length} reviewed
//                     </p>
//                   </div>
//                 </div>
//                 <ul className="divide-y divide-gray-50">
//                   {activeQuestions.map((q) => (
//                     <QuestionItem key={q.id} q={q} expanded={expandedId === q.id} onExpand={() => setExpandedId(expandedId === q.id ? null : q.id)} onToggle={() => toggleDone(activeCategory, q.id)} />
//                   ))}
//                 </ul>
//               </Card>
//             </div>
//           </div>
//         )}
//       </div>
//     </EmployeeLayout>
//   );
// }

// function QuestionItem({ q, expanded, onExpand, onToggle }: { q: Question; expanded: boolean; onExpand: () => void; onToggle: () => void }) {
//   return (
//     <li className={`transition-colors ${q.done ? 'bg-emerald-50/40' : ''}`}>
//       <div className="flex items-start gap-3 px-5 py-4 cursor-pointer" onClick={onExpand}>
//         <button onClick={(e) => { e.stopPropagation(); onToggle(); }} className="mt-0.5 shrink-0">
//           {q.done
//             ? <CheckCircle size={18} className="text-emerald-500" />
//             : <Circle size={18} className="text-gray-300 hover:text-indigo-400 transition-colors" />}
//         </button>
//         <div className="flex-1 min-w-0">
//           <div className="flex items-center gap-2 flex-wrap mb-0.5">
//             <p className={`text-sm font-medium ${q.done ? 'text-gray-500 line-through' : 'text-gray-900'}`}>{q.question}</p>
//             <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${DIFF_STYLES[q.difficulty]}`}>
//               {q.difficulty.charAt(0).toUpperCase() + q.difficulty.slice(1)}
//             </span>
//           </div>
//         </div>
//         {expanded ? <ChevronUp size={16} className="text-gray-400 shrink-0 mt-1" /> : <ChevronDown size={16} className="text-gray-400 shrink-0 mt-1" />}
//       </div>
//       {expanded && (
//         <div className="px-5 pb-5 pl-16">
//           <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
//             <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-2">Sample Answer</p>
//             <p className="text-sm text-gray-700 leading-relaxed">{q.answer}</p>
//           </div>
//         </div>
//       )}
//     </li>
//   );
// }
