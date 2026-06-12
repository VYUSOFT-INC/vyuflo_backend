// src/pages/admin/Roles&permissions.tsx
// Mobile responsive: aside stacks above main on mobile, side-by-side on lg+
import { useState, useEffect } from "react";

import imgShield from "../../assets/admin/shield.svg";
import imgUsers  from "../../assets/admin/users.svg";
import imgEye    from "../../assets/admin/eye.svg";
import imgFile   from "../../assets/admin/file.svg";
import imgPlus   from "../../assets/admin/plus.svg";
import imgSearch from "../../assets/admin/search.svg";
import imgCopy   from "../../assets/admin/copy.svg";
import imgEdit   from "../../assets/admin/edit.svg";

import { useRoles, usePermissions } from "../../hooks/admin/useRoles";
import {
  createRole, updateRole, deleteRole,
  assignPermissionToRole, removePermissionFromRole,
} from "../../api/admin/roles.api";

interface Permission {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
}

interface PermissionGroup {
  label: string;
  icon: string;
  permissions: Record<string, Permission>;
}

interface Role {
  id: string;
  category: "predefined" | "custom";
  role: string;
  display_name: string;
  roleType: string;
  description: string;
  isSystemRole: boolean;
  userCount: number;
  permissionGroups: Record<string, PermissionGroup>;
}

const PREDEFINED_ROLES = ["app_admin", "hr", "employee", "attorney"];

const titleCase = (s: string) =>
  s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const ROLE_ICON_MAP: Record<string, string> = {
  app_admin: imgShield, hr: imgUsers, employee: imgEye, attorney: imgFile,
};

const GROUP_ICON_MAP: Record<string, string> = {
  users: imgUsers, file: imgFile, user_management: imgUsers, visa_processing: imgFile,
};

interface ToggleProps {
  enabled: boolean;
  onChange: (val: boolean) => void;
  disabled: boolean;
}

const Toggle = ({ enabled, onChange, disabled }: ToggleProps) => (
  <button
    onClick={() => !disabled && onChange(!enabled)}
    style={{
      width: 44, height: 24, borderRadius: 12, border: "none",
      background: enabled ? "#4F46E5" : "#D1D5DB",
      position: "relative", cursor: disabled ? "not-allowed" : "pointer",
      transition: "background 0.2s", flexShrink: 0, opacity: disabled ? 0.6 : 1,
    }}
  >
    <span style={{
      position: "absolute", top: 3, left: enabled ? 23 : 3,
      width: 18, height: 18, borderRadius: "50%", background: "#fff",
      transition: "left 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
    }} />
  </button>
);

interface PermissionRowProps {
  label: string;
  description: string;
  enabled: boolean;
  onChange: (val: boolean) => void;
  isSystemRole: boolean;
}

const PermissionRow = ({ label, description, enabled, onChange, isSystemRole }: PermissionRowProps) => (
  <div className="flex items-start justify-between gap-3" style={{ padding: "14px 0", borderBottom: "1px solid #F3F4F6" }}>
    <div style={{ flex: 1 }}>
      <div style={{ fontWeight: 500, fontSize: 14, color: "#111827" }}>{label}</div>
      <div style={{ fontSize: 12, color: "#6B7280", marginTop: 2 }}>{description}</div>
    </div>
    <Toggle enabled={enabled} onChange={onChange} disabled={isSystemRole} />
  </div>
);

interface PermissionCardProps {
  title: string;
  iconSrc: string;
  permissions: Record<string, Permission>;
  isSystemRole: boolean;
  onToggle: (permKey: string, val: boolean) => void;
}

const PermissionCard = ({ title, iconSrc, permissions, isSystemRole, onToggle }: PermissionCardProps) => {
  const enabledCount = Object.values(permissions).filter((p) => p.enabled).length;
  const total = Object.values(permissions).length;

  return (
    <div className="w-full sm:flex-1 sm:min-w-[280px]"
      style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 12, padding: "20px 24px" }}>
      <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
        <div className="flex items-center gap-[10px]">
          <div style={{ width: 36, height: 36, borderRadius: 8, background: "#EEF2FF", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <img src={iconSrc} alt="" width={20} height={20}
              style={{ filter: "invert(29%) sepia(98%) saturate(1000%) hue-rotate(230deg)" }} />
          </div>
          <span style={{ fontWeight: 600, fontSize: 15, color: "#111827" }}>{title}</span>
        </div>
        <span style={{ fontSize: 12, color: "#6B7280" }}>{enabledCount}/{total} Enabled</span>
      </div>

      {Object.entries(permissions).map(([key, perm]) => (
        <PermissionRow key={key} label={perm.label} description={perm.description}
          enabled={perm.enabled} isSystemRole={isSystemRole}
          onChange={(val) => onToggle(key, val)} />
      ))}
    </div>
  );
};

interface RoleItemProps {
  name: string;
  description: string;
  userCount: number;
  iconSrc: string;
  active: boolean;
  onClick: () => void;
}

const RoleItem = ({ name, description, userCount, iconSrc, active, onClick }: RoleItemProps) => (
  <div onClick={onClick}
    className="flex items-center gap-[10px] cursor-pointer"
    style={{
      padding: "10px 12px", borderRadius: 8,
      background: active ? "#EEF2FF" : "transparent", marginBottom: 4,
    }}>
    <div className="shrink-0" style={{
      width: 32, height: 32, borderRadius: 8,
      background: active ? "#4F46E5" : "#F3F4F6",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <img src={iconSrc} alt="" width={16} height={16}
        style={{ filter: active ? "brightness(0) invert(1)" : "invert(45%) sepia(0%) saturate(0%) hue-rotate(0deg)" }} />
    </div>
    <div className="flex-1 min-w-0">
      <div className="truncate" style={{ fontWeight: 600, fontSize: 13, color: active ? "#4F46E5" : "#111827" }}>{name}</div>
      <div className="truncate" style={{ fontSize: 11, color: "#9CA3AF" }}>{description}</div>
    </div>
    <span className="shrink-0 whitespace-nowrap"
      style={{ fontSize: 11, color: "#6B7280", background: "#F3F4F6", padding: "2px 7px", borderRadius: 20 }}>
      {userCount} Users
    </span>
  </div>
);

interface CreateRoleModalProps {
  onClose: () => void;
  onCreateRole: (data: { roleName: string; description: string }) => void;
}

const CreateRoleModal = ({ onClose, onCreateRole }: CreateRoleModalProps) => {
  const [roleName, setRoleName] = useState("");
  const [description, setDescription] = useState("");

  const handleCreate = () => {
    if (roleName.trim()) { onCreateRole({ roleName, description }); onClose(); }
  };

  return (
    <div onClick={onClose}
      className="fixed inset-0 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.4)", zIndex: 1000, backdropFilter: "blur(2px)" }}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[460px]"
        style={{ background: "#fff", borderRadius: 14, padding: "28px 24px 20px", boxShadow: "0 12px 48px rgba(0,0,0,0.18)" }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111827", marginBottom: 6, marginTop: 0 }}>Create custom role</h2>
        <p style={{ fontSize: 13.5, color: "#6B7280", marginBottom: 20, lineHeight: 1.5 }}>
          Define a new role and assign permissions from existing modules.
        </p>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>Role name</label>
          <input type="text" placeholder="e.g. Compliance Officer" value={roleName}
            onChange={(e) => setRoleName(e.target.value)}
            style={{ width: "100%", padding: "10px 14px", border: "1.5px solid #D1D5DB", borderRadius: 8, fontSize: 14, color: "#111827", outline: "none", boxSizing: "border-box" }} />
        </div>
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>Description</label>
          <textarea placeholder="What does this role do?" value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={{ width: "100%", padding: "10px 14px", border: "1.5px solid #D1D5DB", borderRadius: 8, fontSize: 14, color: "#111827", outline: "none", boxSizing: "border-box", minHeight: 90, resize: "vertical", fontFamily: "inherit" }} />
        </div>
        <div className="flex justify-end gap-[10px]">
          <button onClick={onClose} style={{ padding: "9px 20px", border: "1.5px solid #D1D5DB", borderRadius: 8, background: "#fff", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Cancel</button>
          <button onClick={handleCreate} disabled={!roleName.trim()}
            style={{ padding: "9px 20px", border: "none", borderRadius: 8, background: roleName.trim() ? "#4F46E5" : "#A5B4FC", fontSize: 14, fontWeight: 600, color: "#fff", cursor: roleName.trim() ? "pointer" : "not-allowed" }}>Create role</button>
        </div>
      </div>
    </div>
  );
};

interface EditDetailsModalProps {
  role: Role;
  onClose: () => void;
  onSave: (id: string, data: { name: string; description: string }) => void;
  onDelete: (id: string) => void;
}

const EditDetailsModal = ({ role, onClose, onSave, onDelete }: EditDetailsModalProps) => {
  const [name, setName] = useState(role.role);
  const [description, setDescription] = useState(role.description ?? "");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleSave = () => { if (name.trim()) { onSave(role.id, { name, description }); onClose(); } };
  const handleDelete = () => { onDelete(role.id); onClose(); };

  return (
    <div onClick={onClose}
      className="fixed inset-0 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.4)", zIndex: 1000, backdropFilter: "blur(2px)" }}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[460px]"
        style={{ background: "#fff", borderRadius: 14, padding: "28px 24px 20px", boxShadow: "0 12px 48px rgba(0,0,0,0.18)" }}>
        {!showDeleteConfirm ? (
          <>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111827", marginBottom: 6, marginTop: 0 }}>Edit role details</h2>
            <p style={{ fontSize: 13.5, color: "#6B7280", marginBottom: 20, lineHeight: 1.5 }}>Update the name and description for this role.</p>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>Role name</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                style={{ width: "100%", padding: "10px 14px", border: "1.5px solid #D1D5DB", borderRadius: 8, fontSize: 14, color: "#111827", outline: "none", boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>Description</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this role do?"
                style={{ width: "100%", padding: "10px 14px", border: "1.5px solid #D1D5DB", borderRadius: 8, fontSize: 14, color: "#111827", outline: "none", boxSizing: "border-box", minHeight: 90, resize: "vertical", fontFamily: "inherit" }} />
            </div>
            <div style={{ borderTop: "1px solid #F3F4F6", paddingTop: 16, marginBottom: 16 }}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#EF4444" }}>Delete role</div>
                  <div style={{ fontSize: 12, color: "#9CA3AF", marginTop: 2 }}>
                    This action cannot be undone. All users with this role will be affected.
                  </div>
                </div>
                <button onClick={() => setShowDeleteConfirm(true)}
                  className="self-start sm:self-auto"
                  style={{ padding: "7px 14px", border: "1.5px solid #FCA5A5", borderRadius: 8, background: "#FFF5F5", fontSize: 13, fontWeight: 600, color: "#EF4444", cursor: "pointer" }}>
                  Delete
                </button>
              </div>
            </div>
            <div className="flex justify-end gap-[10px]">
              <button onClick={onClose} style={{ padding: "9px 20px", border: "1.5px solid #D1D5DB", borderRadius: 8, background: "#fff", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Cancel</button>
              <button onClick={handleSave} disabled={!name.trim()}
                style={{ padding: "9px 20px", border: "none", borderRadius: 8, background: name.trim() ? "#4F46E5" : "#A5B4FC", fontSize: 14, fontWeight: 600, color: "#fff", cursor: name.trim() ? "pointer" : "not-allowed" }}>Save changes</button>
            </div>
          </>
        ) : (
          <>
            <div style={{ textAlign: "center", padding: "8px 0 16px" }}>
              <div style={{ width: 52, height: 52, borderRadius: "50%", background: "#FEE2E2", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                <span style={{ fontSize: 24 }}>🗑️</span>
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111827", marginBottom: 8, marginTop: 0 }}>Delete "{role.role}"?</h2>
              <p style={{ fontSize: 14, color: "#6B7280", lineHeight: 1.6 }}>
                This will permanently delete the role. Users assigned this role will lose their permissions. This action <strong>cannot be undone</strong>.
              </p>
            </div>
            <div className="flex gap-[10px]" style={{ marginTop: 8 }}>
              <button onClick={() => setShowDeleteConfirm(false)} style={{ flex: 1, padding: "10px 0", border: "1.5px solid #D1D5DB", borderRadius: 8, background: "#fff", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Cancel</button>
              <button onClick={handleDelete} style={{ flex: 1, padding: "10px 0", border: "none", borderRadius: 8, background: "#EF4444", fontSize: 14, fontWeight: 600, color: "#fff", cursor: "pointer" }}>Yes, delete role</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default function RolesPermissionsEditor() {
  const { data: rolesData, isLoading, error, refetch: refetchRoles } = useRoles();
  const { data: permissions } = usePermissions();

  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);

  useEffect(() => {
    const mapped: Role[] = rolesData.map((item) => {
      const isPredef = PREDEFINED_ROLES.includes(item.name.toLowerCase());
      return {
        id: item.id,
        category: isPredef ? "predefined" : "custom",
        role: item.name,
        display_name: item.display_name || item.name,
        roleType: isPredef ? "System Role" : "Custom Role",
        isSystemRole: false,
        description: item.description,
        userCount: item.user_count,
        permissionGroups: {},
      };
    });
    setRoles(mapped);
    setSelectedRoleId((prev) => prev || (mapped[0]?.id ?? ""));
  }, [rolesData]);

  useEffect(() => {
    if (!selectedRoleId || permissions.length === 0) return;
    const apiRole = rolesData.find((r) => r.id === selectedRoleId);
    const roleName = apiRole?.name ?? "";

    const groups: Record<string, PermissionGroup> = {};
    permissions.forEach((perm) => {
      const mod = perm.module;
      if (!groups[mod]) groups[mod] = { label: titleCase(mod), icon: mod, permissions: {} };
      groups[mod].permissions[perm.code] = {
        id: perm.id, label: perm.description, description: perm.code,
        enabled: perm.roles_assigned.includes(roleName),
      };
    });

    setRoles((prev) => prev.map((r) =>
      r.id === selectedRoleId ? { ...r, permissionGroups: groups } : r
    ));
  }, [selectedRoleId, permissions, rolesData]);

  const handleToggle = async (groupKey: string, permKey: string, val: boolean) => {
    const role = roles.find((r) => r.id === selectedRoleId);
    if (!role || role.isSystemRole) return;
    const perm = role.permissionGroups[groupKey]?.permissions[permKey];
    if (!perm) return;

    const setEnabled = (enabled: boolean) =>
      setRoles((prev) => prev.map((r) => {
        if (r.id !== selectedRoleId) return r;
        return {
          ...r,
          permissionGroups: {
            ...r.permissionGroups,
            [groupKey]: {
              ...r.permissionGroups[groupKey],
              permissions: {
                ...r.permissionGroups[groupKey].permissions,
                [permKey]: { ...perm, enabled },
              },
            },
          },
        };
      }));

    setEnabled(val);
    try {
      if (val) await assignPermissionToRole(selectedRoleId, perm.id);
      else     await removePermissionFromRole(selectedRoleId, perm.id);
    } catch {
      setEnabled(!val);
      alert("Could not save this change. Please try again.");
    }
  };

  const handleCreateRole = async ({ roleName, description }: { roleName: string; description: string }) => {
    try {
      const created = await createRole({ name: roleName, description });
      await refetchRoles();
      if (created?.id) setSelectedRoleId(created.id);
    } catch { alert("Could not create role."); }
  };

  const handleEditRole = async (id: string, data: { name: string; description: string }) => {
    try { await updateRole(id, data); await refetchRoles(); }
    catch { alert("Could not update role."); }
  };

  const handleDeleteRole = async (id: string) => {
    try {
      await deleteRole(id);
      setSelectedRoleId((prev) => (prev === id ? "" : prev));
      await refetchRoles();
    } catch { alert("Could not delete role."); }
  };

  const filteredRoles = roles.filter((r) =>
    r.role.toLowerCase().includes(search.toLowerCase()) ||
    r.display_name.toLowerCase().includes(search.toLowerCase()) ||
    r.description?.toLowerCase().includes(search.toLowerCase())
  );
  const predefined = filteredRoles.filter((r) => r.category === "predefined");
  const custom = filteredRoles.filter((r) => r.category === "custom");
  const selectedRole = roles.find((r) => r.id === selectedRoleId) ?? roles[0];

  return (
    <div className="flex flex-col min-h-screen"
      style={{ fontFamily: "'Inter', -apple-system, sans-serif", background: "#F9FAFB" }}>

      {/* ── Container: STACKS on mobile, SIDE-BY-SIDE on lg+ ── */}
      <div className="flex flex-1 flex-col lg:flex-row" style={{ overflow: "hidden" }}>

        {/* ── Sidebar: full-width on mobile, 240px on desktop ── */}
        <aside className="w-full lg:w-[240px] flex flex-col gap-2"
          style={{
            background: "#fff",
            borderBottom: "1px solid #E5E7EB",
            padding: "20px 16px",
          }}>
          <div style={{ fontWeight: 600, fontSize: 15, color: "#111827", marginBottom: 12, paddingLeft: 4 }}>
            Roles & Permissions
          </div>

          <div className="relative" style={{ marginBottom: 12 }}>
            <img src={imgSearch} alt="" width={14} height={14}
              style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", opacity: 0.4 }} />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search roles..."
              style={{ width: "100%", padding: "7px 10px 7px 30px", border: "1px solid #E5E7EB", borderRadius: 8, fontSize: 13, color: "#374151", outline: "none", boxSizing: "border-box" }} />
          </div>

          {error && (
            <div style={{ background: "#FEF3C7", border: "1px solid #FCD34D", borderRadius: 8, padding: "8px 10px", fontSize: 11, color: "#92400E", marginBottom: 8 }}>
              ⚠️ {error}
            </div>
          )}
          {isLoading && (
            <div style={{ fontSize: 12, color: "#9CA3AF", textAlign: "center", padding: "8px 0" }}>Loading from API…</div>
          )}

          <div className="flex justify-between" style={{ fontSize: 11, fontWeight: 600, color: "#9CA3AF", letterSpacing: "0.05em", marginBottom: 4, marginTop: 4 }}>
            <span>PREDEFINED ROLES</span>
            <span>{predefined.length}</span>
          </div>
          {predefined.map((role) => (
            <RoleItem key={role.id} name={role.display_name}
              description={(role.description?.slice(0, 30) ?? "") + ((role.description?.length ?? 0) > 30 ? "…" : "")}
              userCount={role.userCount}
              iconSrc={ROLE_ICON_MAP[role.role.toLowerCase()] ?? imgShield}
              active={selectedRoleId === role.id}
              onClick={() => setSelectedRoleId(role.id)} />
          ))}

          {custom.length > 0 && (
            <>
              <div className="flex justify-between" style={{ fontSize: 11, fontWeight: 600, color: "#9CA3AF", letterSpacing: "0.05em", marginTop: 12, marginBottom: 4 }}>
                <span>CUSTOM ROLES</span>
                <span>{custom.length}</span>
              </div>
              {custom.map((role) => (
                <RoleItem key={role.id} name={role.display_name}
                  description={(role.description?.slice(0, 30) ?? "") + ((role.description?.length ?? 0) > 30 ? "…" : "")}
                  userCount={role.userCount}
                  iconSrc={ROLE_ICON_MAP[role.role.toLowerCase()] ?? imgUsers}
                  active={selectedRoleId === role.id}
                  onClick={() => setSelectedRoleId(role.id)} />
              ))}
            </>
          )}

          {/* <div className="hidden lg:block" style={{ flex: 1 }} /> */}

          <button onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center justify-center gap-[6px]"
            style={{
              width: "100%", padding: "10px 0", background: "#4F46E5",
              color: "#fff", border: "none", borderRadius: 8,
              fontWeight: 600, fontSize: 13, cursor: "pointer", marginTop: 12,
            }}>
            <img src={imgPlus} alt="" width={16} height={16}
              style={{ filter: "brightness(0) invert(1)" }} />
            Create Custom Role
          </button>
        </aside>

        {/* ── Main Content ── */}
        <main className="flex-1 p-4 sm:p-6 lg:p-7" style={{ overflowY: "auto" }}>
          {selectedRole ? (
            <>
              {/* Role header card */}
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
                style={{ background: "#fff", border: "1px solid #E5E7EB", borderRadius: 12, padding: "20px 24px", marginBottom: 20 }}>
                <div className="flex items-start gap-4 min-w-0">
                  <div className="shrink-0" style={{ width: 44, height: 44, borderRadius: 10, background: "#EEF2FF", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <img src={ROLE_ICON_MAP[selectedRole.role.toLowerCase()] ?? imgShield} alt="" width={22} height={22}
                      style={{ filter: "invert(29%) sepia(98%) saturate(1000%) hue-rotate(230deg)" }} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span style={{ fontWeight: 700, fontSize: 20, color: "#111827" }}>{selectedRole.role}</span>
                      <span className="whitespace-nowrap" style={{ fontSize: 11, fontWeight: 600, background: "#EEF2FF", color: "#4F46E5", padding: "3px 8px", borderRadius: 20 }}>
                        {selectedRole.roleType}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: "#6B7280", marginTop: 4 }}>
                      {selectedRole.description}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 sm:gap-[10px] sm:shrink-0">
                  <button className="flex items-center gap-[6px]"
                    style={{ padding: "8px 14px", border: "1px solid #E5E7EB", borderRadius: 8, background: "#fff", fontSize: 13, cursor: "pointer", color: "#374151" }}>
                    <img src={imgCopy} alt="" width={14} height={14} />
                    Duplicate
                  </button>
                  <button onClick={() => setIsEditModalOpen(true)}
                    className="flex items-center gap-[6px]"
                    style={{ padding: "8px 14px", border: "1px solid #E5E7EB", borderRadius: 8, background: "#fff", fontSize: 13, cursor: "pointer", color: "#374151" }}>
                    <img src={imgEdit} alt="" width={14} height={14} />
                    <span className="whitespace-nowrap">Edit Details</span>
                  </button>
                  {selectedRole.category === "custom" && (
                    <button onClick={() => setIsDeleteModalOpen(true)}
                      className="flex items-center gap-[6px]"
                      style={{ padding: "8px 14px", border: "1px solid #FCA5A5", borderRadius: 8, background: "#FFF5F5", fontSize: 13, cursor: "pointer", color: "#EF4444", fontWeight: 600 }}>
                      🗑️ Delete
                    </button>
                  )}
                </div>
              </div>

              {/* Permission group cards — STACKS on mobile, wraps on tablet+ */}
              <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
                {Object.entries(selectedRole.permissionGroups ?? {}).map(([groupKey, group]) => (
                  <PermissionCard key={groupKey} title={group.label}
                    iconSrc={GROUP_ICON_MAP[group.icon] ?? GROUP_ICON_MAP[groupKey] ?? imgFile}
                    permissions={group.permissions}
                    isSystemRole={selectedRole.isSystemRole}
                    onToggle={(permKey, val) => handleToggle(groupKey, permKey, val)} />
                ))}
              </div>

              {selectedRole.isSystemRole && (
                <div style={{ marginTop: 16, padding: "10px 16px", background: "#FEF3C7", border: "1px solid #FCD34D", borderRadius: 8, fontSize: 13, color: "#92400E" }}>
                  ⚠️ This is a System Role — permissions are locked and cannot be modified.
                </div>
              )}
            </>
          ) : (
            <div style={{ textAlign: "center", color: "#9CA3AF", marginTop: 60 }}>
              Select a role to view permissions.
            </div>
          )}
        </main>
      </div>

      {isCreateModalOpen && (
        <CreateRoleModal onClose={() => setIsCreateModalOpen(false)} onCreateRole={handleCreateRole} />
      )}

      {isEditModalOpen && selectedRole && (
        <EditDetailsModal role={selectedRole} onClose={() => setIsEditModalOpen(false)}
          onSave={handleEditRole} onDelete={handleDeleteRole} />
      )}

      {isDeleteModalOpen && selectedRole && (
        <div onClick={() => setIsDeleteModalOpen(false)}
          className="fixed inset-0 flex items-center justify-center p-4"
          style={{ background: "rgba(0,0,0,0.4)", zIndex: 1000, backdropFilter: "blur(2px)" }}>
          <div onClick={(e) => e.stopPropagation()}
            className="w-full max-w-[420px]"
            style={{ background: "#fff", borderRadius: 14, padding: "28px 24px 20px", boxShadow: "0 12px 48px rgba(0,0,0,0.18)" }}>
            <div style={{ textAlign: "center", padding: "8px 0 16px" }}>
              <div style={{ width: 52, height: 52, borderRadius: "50%", background: "#FEE2E2", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                <span style={{ fontSize: 24 }}>🗑️</span>
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111827", marginBottom: 8, marginTop: 0 }}>Delete "{selectedRole.display_name}"?</h2>
              <p style={{ fontSize: 14, color: "#6B7280", lineHeight: 1.6 }}>
                This will permanently delete the role. Users assigned this role will lose their permissions. This action <strong>cannot be undone</strong>.
              </p>
            </div>
            <div className="flex gap-[10px]" style={{ marginTop: 8 }}>
              <button onClick={() => setIsDeleteModalOpen(false)}
                style={{ flex: 1, padding: "10px 0", border: "1.5px solid #D1D5DB", borderRadius: 8, background: "#fff", fontSize: 14, fontWeight: 500, color: "#374151", cursor: "pointer" }}>Cancel</button>
              <button onClick={() => { handleDeleteRole(selectedRole.id); setIsDeleteModalOpen(false); }}
                style={{ flex: 1, padding: "10px 0", border: "none", borderRadius: 8, background: "#EF4444", fontSize: 14, fontWeight: 600, color: "#fff", cursor: "pointer" }}>Yes, delete role</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
