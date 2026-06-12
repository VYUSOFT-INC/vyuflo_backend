// import { useState, type ReactNode } from 'react';
// import { Search, ChevronDown, ChevronUp, MessageSquare, Mail, Phone, ExternalLink, ArrowRight, BookOpen, FileQuestion, Zap, HelpCircle } from 'lucide-react';
// import EmployeeLayout from '../../components/layout/EmployeeLayout';

// function Card({ children, className = '', padding = 'md' }: { children: ReactNode; className?: string; padding?: 'none' | 'sm' | 'md' | 'lg' }) {
//   const p = { none: '', sm: 'p-4', md: 'p-6', lg: 'p-8' };
//   return <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${p[padding]} ${className}`}>{children}</div>;
// }

// interface FaqItem { id: string; question: string; answer: string; category: string; }

// const faqs: FaqItem[] = [
//   { id: 'f1', category: 'Account', question: 'How do I reset my password?', answer: 'Click "Forgot Password" on the login page and enter your email address. You\'ll receive a link to reset your password. If you don\'t receive the email within 5 minutes, check your spam folder or contact support.' },
//   { id: 'f2', category: 'Cases', question: 'How long does H-1B processing take?', answer: 'Standard H-1B processing typically takes 3-6 months. With Premium Processing ($2,805 fee), USCIS guarantees a response within 15 business days. Processing times may vary based on service center workload and case complexity.' },
//   { id: 'f3', category: 'Documents', question: 'What file formats are accepted for document uploads?', answer: 'We accept PDF, DOC, DOCX, JPG, JPEG, and PNG files. Maximum file size is 25 MB per document. For best results, upload scanned documents at 300 DPI or higher for readability.' },
//   { id: 'f4', category: 'Cases', question: 'How do I check my case status?', answer: 'Log in and navigate to "My Applications" to see all your cases. Each case shows the current status and stage. You can also view the complete timeline in the case detail view. USCIS status can be checked at USCIS.gov using your receipt number.' },
//   { id: 'f5', category: 'Documents', question: 'Why was my document rejected?', answer: 'Documents may be rejected for: unclear/blurry scan, missing pages, expired document, incorrect document type, or not meeting minimum requirements. Check the rejection message for the specific reason and re-upload accordingly.' },
//   { id: 'f6', category: 'Billing', question: 'What payment methods are accepted?', answer: 'We accept all major credit/debit cards (Visa, Mastercard, American Express, Discover), ACH bank transfers, and wire transfers. All payments are processed securely through Stripe.' },
//   { id: 'f7', category: 'Messaging', question: 'How does secure messaging work?', answer: 'Messages between you and your attorney team are end-to-end encrypted. You can exchange files and documents directly in the chat. Message history is permanently stored for your records and available in your account.' },
//   { id: 'f8', category: 'Account', question: 'Can I have multiple cases at the same time?', answer: 'Yes, you can manage multiple immigration cases simultaneously. Each case has its own dedicated workspace with separate document sets, timelines, and communication threads.' },
// ];

// const FAQ_CATEGORIES = ['All', 'Account', 'Cases', 'Documents', 'Messaging', 'Billing'];

// interface HelpCategory { id: string; label: string; icon: ReactNode; description: string; color: string; }

// const HELP_CATEGORIES: HelpCategory[] = [
//   { id: 'getting-started', label: 'Getting Started', icon: <Zap size={20} />, description: 'New to VisaFlow? Start here.', color: 'bg-indigo-50 text-indigo-600' },
//   { id: 'immigration', label: 'Immigration Process', icon: <BookOpen size={20} />, description: 'Guides for visa types and processes.', color: 'bg-blue-50 text-blue-600' },
//   { id: 'documents', label: 'Documents & Forms', icon: <FileQuestion size={20} />, description: 'Document requirements and formats.', color: 'bg-emerald-50 text-emerald-600' },
//   { id: 'account', label: 'Account & Billing', icon: <HelpCircle size={20} />, description: 'Manage your account and payments.', color: 'bg-purple-50 text-purple-600' },
// ];

// const POPULAR_ARTICLES = [
//   'H-1B Petition Complete Guide',
//   'Understanding the Visa Bulletin',
//   'OPT STEM Extension Step-by-Step',
//   'How to Upload Documents Correctly',
//   'Priority Date and Visa Number Explained',
// ];

// export default function HelpSupport() {
//   const [search, setSearch] = useState('');
//   const [faqCategory, setFaqCategory] = useState('All');
//   const [expandedFaq, setExpandedFaq] = useState<string | null>(null);

//   const filteredFaqs = faqs.filter((f) => {
//     const matchCat = faqCategory === 'All' || f.category === faqCategory;
//     const matchSearch = !search || f.question.toLowerCase().includes(search.toLowerCase()) || f.answer.toLowerCase().includes(search.toLowerCase());
//     return matchCat && matchSearch;
//   });

//   return (
//     <EmployeeLayout>
//       <div className="space-y-8">
//         {/* Hero search */}
//         <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl px-8 py-10 text-center">
//           <h1 className="text-3xl font-bold text-white mb-2">How can we help?</h1>
//           <p className="text-indigo-200 mb-6 text-sm">Search our knowledge base or browse topics below</p>
//           <div className="max-w-xl mx-auto relative">
//             <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
//             <input
//               type="text"
//               placeholder="Search for answers..."
//               value={search}
//               onChange={(e) => setSearch(e.target.value)}
//               className="w-full pl-12 pr-4 py-3 rounded-xl text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-white/50 shadow-lg"
//             />
//           </div>
//         </div>

//         {/* Help categories */}
//         {!search && (
//           <div>
//             <h2 className="text-base font-semibold text-gray-900 mb-4">Browse by Topic</h2>
//             <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
//               {HELP_CATEGORIES.map((cat) => (
//                 <Card key={cat.id} padding="sm" className="cursor-pointer hover:border-indigo-200 hover:shadow-md transition-all group">
//                   <div className={`w-10 h-10 rounded-xl ${cat.color} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
//                     {cat.icon}
//                   </div>
//                   <p className="text-sm font-semibold text-gray-900">{cat.label}</p>
//                   <p className="text-xs text-gray-500 mt-0.5">{cat.description}</p>
//                   <div className="flex items-center gap-1 mt-3 text-xs text-indigo-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
//                     View articles <ArrowRight size={12} />
//                   </div>
//                 </Card>
//               ))}
//             </div>
//           </div>
//         )}

//         {/* Main content: FAQ + sidebar */}
//         <div className="flex flex-col lg:flex-row gap-6">
//           {/* FAQ */}
//           <div className="flex-1 min-w-0 space-y-4">
//             <div className="flex items-center justify-between gap-4 flex-wrap">
//               <h2 className="text-base font-semibold text-gray-900">
//                 {search ? `Search results for "${search}"` : 'Frequently Asked Questions'}
//               </h2>
//               <div className="flex gap-2 flex-wrap">
//                 {FAQ_CATEGORIES.map((cat) => (
//                   <button key={cat} onClick={() => setFaqCategory(cat)}
//                     className={['px-3.5 py-1.5 rounded-full text-xs font-medium border transition-colors',
//                       faqCategory === cat ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'].join(' ')}>
//                     {cat}
//                   </button>
//                 ))}
//               </div>
//             </div>

//             {filteredFaqs.length === 0 ? (
//               <Card>
//                 <div className="py-12 text-center">
//                   <Search size={32} className="mx-auto mb-3 text-gray-300" />
//                   <p className="text-gray-500 font-medium">No results found</p>
//                   <p className="text-sm text-gray-400 mt-1">Try different keywords or contact us directly</p>
//                 </div>
//               </Card>
//             ) : (
//               <Card padding="none">
//                 <ul className="divide-y divide-gray-100">
//                   {filteredFaqs.map((faq) => (
//                     <li key={faq.id}>
//                       <button
//                         onClick={() => setExpandedFaq(expandedFaq === faq.id ? null : faq.id)}
//                         className="w-full flex items-start gap-4 px-5 py-4 text-left hover:bg-gray-50 transition-colors"
//                       >
//                         <div className="flex-1 min-w-0">
//                           <div className="flex items-center gap-2 mb-0.5">
//                             <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">{faq.category}</span>
//                           </div>
//                           <p className={`text-sm font-medium ${expandedFaq === faq.id ? 'text-indigo-700' : 'text-gray-900'}`}>{faq.question}</p>
//                         </div>
//                         {expandedFaq === faq.id
//                           ? <ChevronUp size={16} className="text-indigo-500 shrink-0 mt-1" />
//                           : <ChevronDown size={16} className="text-gray-400 shrink-0 mt-1" />}
//                       </button>
//                       {expandedFaq === faq.id && (
//                         <div className="px-5 pb-5">
//                           <p className="text-sm text-gray-600 leading-relaxed bg-gray-50 rounded-xl p-4">{faq.answer}</p>
//                         </div>
//                       )}
//                     </li>
//                   ))}
//                 </ul>
//               </Card>
//             )}
//           </div>

//           {/* Sidebar */}
//           <div className="lg:w-72 shrink-0 space-y-4">
//             {/* Contact options */}
//             <Card padding="sm">
//               <p className="text-sm font-semibold text-gray-900 mb-3">Contact Support</p>
//               <div className="space-y-3">
//                 <div className="flex items-center gap-3 p-3 rounded-xl border border-gray-100 bg-gray-50 hover:border-indigo-200 hover:bg-indigo-50 cursor-pointer transition-all group">
//                   <div className="w-9 h-9 bg-indigo-100 rounded-lg flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
//                     <MessageSquare size={16} className="text-indigo-600" />
//                   </div>
//                   <div className="flex-1 min-w-0">
//                     <p className="text-xs font-semibold text-gray-900">Live Chat</p>
//                     <p className="text-xs text-emerald-600 font-medium">Available now</p>
//                   </div>
//                   <ArrowRight size={14} className="text-gray-400 group-hover:text-indigo-500 transition-colors" />
//                 </div>
//                 <div className="flex items-center gap-3 p-3 rounded-xl border border-gray-100 bg-gray-50 hover:border-blue-200 hover:bg-blue-50 cursor-pointer transition-all group">
//                   <div className="w-9 h-9 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors">
//                     <Mail size={16} className="text-blue-600" />
//                   </div>
//                   <div className="flex-1 min-w-0">
//                     <p className="text-xs font-semibold text-gray-900">Email Support</p>
//                     <p className="text-xs text-gray-500">24–48 hour response</p>
//                   </div>
//                   <ArrowRight size={14} className="text-gray-400 group-hover:text-blue-500 transition-colors" />
//                 </div>
//                 <div className="flex items-center gap-3 p-3 rounded-xl border border-gray-100 bg-gray-50 hover:border-emerald-200 hover:bg-emerald-50 cursor-pointer transition-all group">
//                   <div className="w-9 h-9 bg-emerald-100 rounded-lg flex items-center justify-center group-hover:bg-emerald-200 transition-colors">
//                     <Phone size={16} className="text-emerald-600" />
//                   </div>
//                   <div className="flex-1 min-w-0">
//                     <p className="text-xs font-semibold text-gray-900">Phone Support</p>
//                     <p className="text-xs text-gray-500">Mon–Fri 9 AM – 6 PM ET</p>
//                   </div>
//                   <ArrowRight size={14} className="text-gray-400 group-hover:text-emerald-500 transition-colors" />
//                 </div>
//               </div>
//             </Card>

//             {/* Popular articles */}
//             <Card padding="sm">
//               <p className="text-sm font-semibold text-gray-900 mb-3">Popular Articles</p>
//               <ul className="space-y-2.5">
//                 {POPULAR_ARTICLES.map((article) => (
//                   <li key={article}>
//                     <button className="flex items-center gap-2 text-left w-full group">
//                       <ExternalLink size={12} className="text-gray-300 group-hover:text-indigo-500 shrink-0 transition-colors" />
//                       <span className="text-sm text-gray-700 group-hover:text-indigo-600 transition-colors">{article}</span>
//                     </button>
//                   </li>
//                 ))}
//               </ul>
//             </Card>

//             {/* Support hours */}
//             <div className="bg-indigo-50 rounded-xl border border-indigo-100 p-4">
//               <p className="text-xs font-semibold text-indigo-700 mb-2">Support Hours</p>
//               <div className="space-y-1 text-xs text-indigo-600">
//                 <div className="flex justify-between"><span>Monday – Friday</span><span className="font-medium">9 AM – 6 PM ET</span></div>
//                 <div className="flex justify-between"><span>Saturday</span><span className="font-medium">10 AM – 4 PM ET</span></div>
//                 <div className="flex justify-between"><span>Sunday</span><span className="font-medium">Closed</span></div>
//               </div>
//             </div>
//           </div>
//         </div>
//       </div>
//     </EmployeeLayout>
//   );
// }
