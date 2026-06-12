// import { useState, type ReactNode } from 'react';
// import { Search, Bookmark, Clock, ArrowRight, TrendingUp } from 'lucide-react';

// import EmployeeLayout from '../../components/layout/EmployeeLayout';

// function Card({ children, className = '', padding = 'md' }: { children: ReactNode; className?: string; padding?: 'none' | 'sm' | 'md' | 'lg' }) {
//   const p = { none: '', sm: 'p-4', md: 'p-6', lg: 'p-8' };
//   return <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${p[padding]} ${className}`}>{children}</div>;
// }

// interface Article {
//   id: string;
//   title: string;
//   excerpt: string;
//   source: string;
//   date: string;
//   readTime: string;
//   category: string;
//   badge?: 'Breaking' | 'Updated' | 'Alert';
//   bookmarked: boolean;
// }

// const articles: Article[] = [
//   { id: '1', title: 'USCIS Announces H-1B Cap Registration for Fiscal Year 2025', excerpt: 'USCIS has opened the H-1B cap registration period. Employers and their representatives must register each prospective H-1B worker electronically through myUSCIS between March 1-18, 2025.', source: 'USCIS.gov', date: 'Apr 18, 2024', readTime: '4 min', category: 'H-1B', badge: 'Breaking', bookmarked: false },
//   { id: '2', title: 'New Rule Expands Automatic Extension for Certain EAD Categories', excerpt: 'DHS published a final rule extending the automatic extension period for Employment Authorization Documents from 180 days to 540 days for certain renewal applicants.', source: 'Federal Register', date: 'Apr 15, 2024', readTime: '3 min', category: 'EAD', badge: 'Updated', bookmarked: true },
//   { id: '3', title: 'DOS Updates Visa Bulletin: Priority Dates Move Forward for EB-2 India', excerpt: 'The Department of State has released the May 2024 Visa Bulletin showing significant forward movement for EB-2 India applicants in the Final Action Dates chart.', source: 'Travel.State.gov', date: 'Apr 12, 2024', readTime: '5 min', category: 'Green Card', bookmarked: false },
//   { id: '4', title: 'STEM OPT Reporting Requirements: Key Reminders for F-1 Students', excerpt: 'SEVP reminds F-1 students on STEM OPT to complete their 6-month self-evaluation in SEVIS and ensure their employer has submitted the required E-Verify enrollment documentation.', source: 'ICE/SEVP', date: 'Apr 10, 2024', readTime: '3 min', category: 'OPT/CPT', badge: 'Alert', bookmarked: false },
//   { id: '5', title: 'Premium Processing Restored for Additional Form Types', excerpt: 'USCIS announced the restoration of premium processing for Form I-140 immigrant petitions under the EB-1 and EB-2 classifications, with a 15-business-day adjudication guarantee.', source: 'USCIS.gov', date: 'Apr 8, 2024', readTime: '2 min', category: 'Policy', bookmarked: true },
//   { id: '6', title: 'L-1B Specialized Knowledge: USCIS Issues Updated Policy Guidance', excerpt: 'USCIS updated its policy guidance on L-1B specialized knowledge determinations, providing clearer standards for what constitutes advanced knowledge of an organization\'s procedures.', source: 'USCIS Policy Manual', date: 'Apr 5, 2024', readTime: '6 min', category: 'L-1', bookmarked: false },
//   { id: '7', title: 'I-485 Processing Times Improve Across Service Centers', excerpt: 'USCIS reports improved processing times for I-485 adjustment of status applications at several service centers, with some cases being adjudicated within 12 months of filing.', source: 'USCIS.gov', date: 'Apr 2, 2024', readTime: '3 min', category: 'Green Card', bookmarked: false },
//   { id: '8', title: 'TN Visa: Updated Profession List Under USMCA', excerpt: 'CBP has issued updated guidance on eligible professions for TN status under USMCA. The list now includes 63 professions across various categories for Canadian and Mexican citizens.', source: 'CBP.gov', date: 'Mar 28, 2024', readTime: '4 min', category: 'TN', bookmarked: false },
// ];

// const CATEGORIES = ['All', 'H-1B', 'Green Card', 'OPT/CPT', 'EAD', 'L-1', 'Policy', 'TN'];

// const BADGE_STYLES: Record<string, string> = {
//   Breaking: 'bg-red-100 text-red-700',
//   Updated: 'bg-blue-100 text-blue-700',
//   Alert: 'bg-amber-100 text-amber-700',
// };

// const TRENDING = [
//   'H-1B lottery results', 'EB-2 NIW processing', 'OPT STEM extension', 'Green card backlog India', 'I-485 wait times',
// ];

// export default function ImmigrationNews() {
//   const [search, setSearch] = useState('');
//   const [activeCategory, setActiveCategory] = useState('All');
//   const [articleList, setArticleList] = useState(articles);

//   const toggleBookmark = (id: string) => {
//     setArticleList((prev) => prev.map((a) => a.id === id ? { ...a, bookmarked: !a.bookmarked } : a));
//   };

//   const filtered = articleList.filter((a) => {
//     const matchCat = activeCategory === 'All' || a.category === activeCategory;
//     const matchSearch = !search || a.title.toLowerCase().includes(search.toLowerCase()) || a.excerpt.toLowerCase().includes(search.toLowerCase());
//     return matchCat && matchSearch;
//   });

//   const featured = filtered[0];
//   const rest = filtered.slice(1);

//   return (
//     <EmployeeLayout>
//       <div className="space-y-6">
//         {/* Header */}
//         <div>
//           <h1 className="text-2xl font-bold text-gray-900">Immigration News</h1>
//           <p className="text-sm text-gray-500 mt-0.5">Stay current with the latest immigration policy updates and USCIS announcements</p>
//         </div>

//         {/* Search */}
//         <div className="relative">
//           <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
//           <input
//             type="text"
//             placeholder="Search news and updates..."
//             value={search}
//             onChange={(e) => setSearch(e.target.value)}
//             className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
//           />
//         </div>

//         {/* Category tabs */}
//         <div className="flex gap-2 flex-wrap">
//           {CATEGORIES.map((cat) => (
//             <button key={cat} onClick={() => setActiveCategory(cat)}
//               className={['px-4 py-1.5 rounded-full text-sm font-medium transition-colors border',
//                 activeCategory === cat ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300 hover:text-indigo-600'].join(' ')}>
//               {cat}
//             </button>
//           ))}
//         </div>

//         <div className="flex flex-col lg:flex-row gap-6">
//           {/* Main feed */}
//           <div className="flex-1 min-w-0 space-y-4">
//             {filtered.length === 0 ? (
//               <Card>
//                 <div className="py-12 text-center">
//                   <Search size={32} className="mx-auto mb-3 text-gray-300" />
//                   <p className="text-gray-500 font-medium">No articles found</p>
//                   <button onClick={() => { setSearch(''); setActiveCategory('All'); }} className="text-sm text-indigo-600 hover:text-indigo-800 mt-2">Clear filters</button>
//                 </div>
//               </Card>
//             ) : (
//               <>
//                 {/* Featured article */}
//                 {featured && (
//                   <Card padding="none" className="overflow-hidden hover:border-indigo-200 transition-colors cursor-pointer">
//                     <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-5">
//                       <div className="flex items-center gap-2 mb-2">
//                         {featured.badge && (
//                           <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full bg-white/20 text-white`}>
//                             {featured.badge}
//                           </span>
//                         )}
//                         <span className="text-xs text-indigo-200 font-medium">{featured.category}</span>
//                       </div>
//                       <h2 className="text-lg font-bold text-white leading-snug mb-2">{featured.title}</h2>
//                       <p className="text-sm text-indigo-100 leading-relaxed line-clamp-2">{featured.excerpt}</p>
//                       <div className="flex items-center justify-between mt-4">
//                         <div className="flex items-center gap-3 text-xs text-indigo-200">
//                           <span>{featured.source}</span>
//                           <span>&middot;</span>
//                           <span>{featured.date}</span>
//                           <span>&middot;</span>
//                           <Clock size={12} className="inline" /> {featured.readTime} read
//                         </div>
//                         <button className="text-white/80 hover:text-white transition-colors">
//                           <Bookmark size={16} className={featured.bookmarked ? 'fill-current' : ''} onClick={(e) => { e.stopPropagation(); toggleBookmark(featured.id); }} />
//                         </button>
//                       </div>
//                     </div>
//                   </Card>
//                 )}

//                 {/* Article list */}
//                 <Card padding="none">
//                   <div className="divide-y divide-gray-100">
//                     {rest.map((article) => (
//                       <div key={article.id} className="group flex gap-4 px-5 py-4 hover:bg-gray-50 cursor-pointer transition-colors">
//                         <div className="flex-1 min-w-0">
//                           <div className="flex items-center gap-2 flex-wrap mb-1">
//                             {article.badge && (
//                               <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${BADGE_STYLES[article.badge]}`}>
//                                 {article.badge}
//                               </span>
//                             )}
//                             <span className="text-xs text-indigo-600 font-medium">{article.category}</span>
//                           </div>
//                           <h3 className="text-sm font-semibold text-gray-900 mb-1 group-hover:text-indigo-700 transition-colors">
//                             {article.title}
//                           </h3>
//                           <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">{article.excerpt}</p>
//                           <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
//                             <span>{article.source}</span>
//                             <span>&middot;</span>
//                             <span>{article.date}</span>
//                             <span>&middot;</span>
//                             <Clock size={11} className="inline" /> {article.readTime}
//                           </div>
//                         </div>
//                         <div className="flex flex-col items-end gap-2">
//                           <button onClick={(e) => { e.stopPropagation(); toggleBookmark(article.id); }}
//                             className={`p-1.5 rounded-lg transition-colors ${article.bookmarked ? 'text-indigo-600 bg-indigo-50' : 'text-gray-300 hover:text-indigo-500 hover:bg-indigo-50'}`}>
//                             <Bookmark size={14} className={article.bookmarked ? 'fill-current' : ''} />
//                           </button>
//                           <ArrowRight size={14} className="text-gray-300 group-hover:text-indigo-500 mt-auto transition-colors" />
//                         </div>
//                       </div>
//                     ))}
//                   </div>
//                 </Card>
//               </>
//             )}
//           </div>

//           {/* Sidebar */}
//           <div className="lg:w-64 shrink-0 space-y-4">
//             {/* Trending */}
//             <Card padding="sm">
//               <div className="flex items-center gap-2 mb-3">
//                 <TrendingUp size={15} className="text-indigo-600" />
//                 <p className="text-sm font-semibold text-gray-900">Trending Topics</p>
//               </div>
//               <ul className="space-y-2">
//                 {TRENDING.map((topic, i) => (
//                   <li key={topic}>
//                     <button
//                       onClick={() => setSearch(topic)}
//                       className="w-full flex items-center gap-2.5 text-left hover:text-indigo-600 transition-colors group"
//                     >
//                       <span className="text-xs font-bold text-gray-300 w-4">{i + 1}</span>
//                       <span className="text-sm text-gray-700 group-hover:text-indigo-600 truncate">{topic}</span>
//                     </button>
//                   </li>
//                 ))}
//               </ul>
//             </Card>

//             {/* Bookmarks */}
//             <Card padding="sm">
//               <div className="flex items-center gap-2 mb-3">
//                 <Bookmark size={15} className="text-indigo-600" />
//                 <p className="text-sm font-semibold text-gray-900">Saved Articles</p>
//               </div>
//               {articleList.filter((a) => a.bookmarked).length === 0 ? (
//                 <p className="text-xs text-gray-400 text-center py-4">No saved articles yet</p>
//               ) : (
//                 <ul className="space-y-2.5">
//                   {articleList.filter((a) => a.bookmarked).map((a) => (
//                     <li key={a.id} className="text-xs">
//                       <p className="font-medium text-gray-800 leading-snug hover:text-indigo-600 cursor-pointer line-clamp-2">{a.title}</p>
//                       <p className="text-gray-400 mt-0.5">{a.date}</p>
//                     </li>
//                   ))}
//                 </ul>
//               )}
//             </Card>

//             {/* Disclaimer */}
//             <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
//               <p className="text-xs text-amber-800 leading-relaxed">
//                 <strong>Disclaimer:</strong> News articles are for informational purposes only and do not constitute legal advice. Consult your immigration attorney for case-specific guidance.
//               </p>
//             </div>
//           </div>
//         </div>
//       </div>
//     </EmployeeLayout>
//   );
// }
