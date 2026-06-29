import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { getUiSession } from './utils/uiSession';
import { getDashboardRoute } from './utils/navigation';

// ── layouts ──────────────────────────────────────────────────────────────────
import { DashboardLayout } from './components/layout/DashboardLayout';

// ── public pages ─────────────────────────────────────────────────────────────
import Login            from './pages/public/Login';
import ForgotPassword   from './pages/public/ForgotPassword';
import Signup           from './pages/public/Signup';
import ResetPasswordOTP from './pages/public/Resetpasswordotp';
import ResetPasswordNew from './pages/public/ResetPasswordNew';
import LinkedInCallback from './pages/public/LinkedInCallback';

// ── onboarding ────────────────────────────────────────────────────────────────
import VerifyEmailPage  from './pages/signup/VerifyEmailPage';
import ProfileSetupPage from './pages/signup/ProfileSetupPage';

// ── employee pages ────────────────────────────────────────────────────────────
import Dashboard             from './pages/employee/Dashboard';
import ApplicationsList      from './pages/employee/ApplicationsList';
import NewApplication        from './pages/employee/NewApplication';
import ApplicationDetail     from './pages/employee/ApplicationDetail';
import DocumentHub           from './pages/employee/DocumentHub';
import DocumentUploadV2      from './pages/employee/DocumentUpload';
import DocumentViewer        from './pages/employee/DocumentViewer';
import SecureMessaging       from './pages/employee/SecureMessaging';
import NotificationsCenterV2 from './pages/employee/NotificationsCenterV2';
import ProfileSecurity       from './pages/employee/ProfileSecurity';
import PaymentsScreen        from './pages/employee/PaymentsScreen';
import SelectAttorney        from './pages/employee/SelectAttorney';
import BookConsultation      from './pages/employee/BookConsultation';
// import ImmigrationNews    from './pages/employee/ImmigrationNews';
// import InterviewPrep      from './pages/employee/InterviewPrep';
// import HelpSupport        from './pages/employee/HelpSupport';

// ── hr pages (uncomment as you build) ────────────────────────────────────────
// import EmployerDashboard  from './pages/hr/EmployerDashboard';

// ── admin pages ───────────────────────────────────────────────────────────────
import AdminDashboard         from './pages/admin/AdminDashboard';
import UserManagement         from './pages/admin/UserManagement';
import RevenueDashboard       from './pages/admin/RevenueDashboard';
import AllTransactions        from './pages/admin/AllTransactions';
import RolesPermissions       from './pages/admin/Roles&permissions';
import SystemSettings         from './pages/admin/SystemSettings';
import NotificationTemplates  from './pages/admin/NotificationTemplates';
import VisaTypesManager       from './pages/admin/VisaTypesManager';
import SystemAuditLogs        from './pages/admin/SystemAuditLogs';
import SubscriptionPricing    from './pages/admin/SubscriptionPricing';
import AdminHelpSupport       from './pages/admin/HelpSupport';


// ── lawyer (attorney) pages ──────────────────────────────────────────────────
import IntakeLanding from './pages/lawyer/intake/IntakeLanding';
import IntakeWizard  from './pages/lawyer/intake/IntakeWizard';

// ─────────────────────────────────────────────────────────────────────────────
// Guards
// ─────────────────────────────────────────────────────────────────────────────

/**
 * PublicRoute — blocks authenticated users from /login, /forgot-password etc.
 * Redirects them straight to their role's dashboard.
 */
function PublicRoute() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  if (isAuthenticated) {
    const session = getUiSession();
    return <Navigate to={getDashboardRoute(session?.roles?.[0] ?? '')} replace />;
  }
  return <Outlet />;
}

/**
 * OnboardingRoute — requires access_token only (no role check).
 * Used for /signup/verify-email and /signup/profile-setup.
 */
function OnboardingRoute() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}

/**
 * RoleRoute — requires auth AND a matching role.
 * Wrong-role users are redirected to their own dashboard instead of a blank/403.
 */
function RoleRoute({ allowedRoles }: { allowedRoles: string[] }) {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const session  = getUiSession();
  const userRole = session?.roles?.[0] ?? '';

  if (!allowedRoles.includes(userRole)) {
    return <Navigate to={getDashboardRoute(userRole)} replace />;
  }
  return <Outlet />;
}

// ─────────────────────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* ── Public (unauthenticated only) ──────────────────────────────── */}
        <Route element={<PublicRoute />}>
          <Route path="/login"           element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
        </Route>

        {/* ── Signup (no auth required) ───────────────────────────────────── */}
        <Route path="/signup" element={<Signup />} />

        {/* ── Onboarding (token required, no role check) ──────────────────── */}
        <Route element={<OnboardingRoute />}>
          <Route path="/signup/verify-email"  element={<VerifyEmailPage />} />
          <Route path="/signup/profile-setup" element={<ProfileSetupPage />} />
        </Route>

        {/* ── Password reset & OAuth callbacks (no auth needed) ───────────── */}
        <Route path="/forgot-password/verify-otp"   element={<ResetPasswordOTP />} />
        <Route path="/forgot-password/new-password" element={<ResetPasswordNew />} />
        <Route path="/auth/linkedin/callback"        element={<LinkedInCallback />} />

        {/* ── EMPLOYEE routes ─────────────────────────────────────────────── */}
        <Route element={<RoleRoute allowedRoles={['employee']} />}>
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard"                        element={<Dashboard />} />
            <Route path="/applications/list"                element={<ApplicationsList />} />
            <Route path="/applications/new"                 element={<NewApplication />} />
            <Route path="/applications/:id"                 element={<ApplicationDetail />} />
            <Route path="/documents"                        element={<DocumentHub />} />
            <Route path="/documents/upload"                 element={<DocumentUploadV2 />} />
            <Route path="/documents/viewer"                 element={<DocumentViewer />} />
            <Route path="/messages"                         element={<SecureMessaging />} />
            <Route path="/notifications"                    element={<NotificationsCenterV2 />} />
            <Route path="/payments"                         element={<PaymentsScreen />} />
            <Route path="/consultations"                    element={<SelectAttorney />} />
            <Route path="/consultations/book/:attorneyId"   element={<BookConsultation />} />
            <Route path="/profile"                          element={<ProfileSecurity />} />
            <Route path="/profile/authentication"           element={<ProfileSecurity />} />
            <Route path="/profile/mfa"                      element={<ProfileSecurity />} />
            <Route path="/profile/login-history"            element={<ProfileSecurity />} />
            <Route path="/profile/privacy"                  element={<ProfileSecurity />} />
            <Route path="/profile/devices"                  element={<ProfileSecurity />} />
            <Route path="/profile/session"                  element={<ProfileSecurity />} />
            <Route path="/profile/security-alerts"          element={<ProfileSecurity />} />
            {/* future employee routes:
            <Route path="/news"           element={<ImmigrationNews />} />
            <Route path="/interview-prep" element={<InterviewPrep />} />
            <Route path="/help"           element={<HelpSupport />} /> */}
          </Route>
        </Route>

        {/* ── HR / EMPLOYER routes ────────────────────────────────────────── */}
        {/* Uncomment block as you build HR pages
        <Route element={<RoleRoute allowedRoles={['hr']} />}>
          <Route element={<DashboardLayout />}>
            <Route path="/employer/dashboard" element={<EmployerDashboard />} />
          </Route>
        </Route> */}

        {/* ── ADMIN routes ────────────────────────────────────────────────── */}
        <Route element={<RoleRoute allowedRoles={['app_admin']} />}>
          <Route element={<DashboardLayout />}>
            <Route path="/admin/dashboard"                       element={<AdminDashboard />} />
            <Route path="/admin/users"                           element={<UserManagement />} />
            <Route path="/admin/revenue-dashboard"               element={<RevenueDashboard />} />
            <Route path="/admin/revenue-dashboard/transactions"  element={<AllTransactions />} />
            <Route path="/admin/roles-permissions"               element={<RolesPermissions />} />
            <Route path="/admin/settings"                        element={<SystemSettings />} />
            <Route path="/admin/notification-templates"          element={<NotificationTemplates />} />
            <Route path="/admin/visa-types"                      element={<VisaTypesManager />} />
            <Route path="/admin/system-audit-logs"               element={<SystemAuditLogs />} />
            <Route path="/admin/subscription-pricing"            element={<SubscriptionPricing />} />
            <Route path="/admin/help-support"                    element={<AdminHelpSupport />} />
          </Route>
        </Route>


        {/* ── ATTORNEY (LAWYER) routes ────────────────────────────────────── */}
        <Route element={<RoleRoute allowedRoles={['attorney']} />}>
          {/* Landing page uses DashboardLayout (sidebar + topbar) */}
          <Route element={<DashboardLayout />}>
            <Route path="/lawyer/intake" element={<IntakeLanding />} />
          </Route>
          {/* Wizard is FULL-SCREEN (own focus-mode header — NO DashboardLayout) */}
          <Route path="/lawyer/intake/:sessionId" element={<IntakeWizard />} />
        </Route>

        {/* ── Catch-all ───────────────────────────────────────────────────── */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
