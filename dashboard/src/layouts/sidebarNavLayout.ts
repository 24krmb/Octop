import type { NavItem, NavSection } from "./sidebarNav";
import {
  BUILTIN_NAV_GROUP_IDS,
  SIDEBAR_NAV_KEYS,
  builtinNavGroupLabelKey,
  isBuiltinNavGroupId,
} from "./sidebarNav";

export interface SidebarNavGroup {
  id: string;
  /** Empty when a built-in group still uses its translated label. */
  name?: string | null;
}

export interface SidebarNavItemPlacement {
  key: string;
  group?: string | null;
  hidden?: boolean;
}

export interface SidebarNavLayout {
  groups: SidebarNavGroup[];
  items: SidebarNavItemPlacement[];
}

export interface SidebarNavEditorState {
  groups: SidebarNavGroup[];
  ungrouped: string[];
  itemsByGroup: Record<string, string[]>;
  hidden: string[];
}

export type SidebarNavItemZone =
  | { kind: "ungrouped" }
  | { kind: "hidden" }
  | { kind: "group"; groupId: string };

const BUILTIN_ID_BY_LABEL: Record<string, string> = {
  "nav.settings": "settings",
  "nav.control": "control",
  "nav.admin": "admin",
};

const NAV_KEY_SET = new Set<string>(SIDEBAR_NAV_KEYS);

export function catalogItems(sections: NavSection[]): Map<string, NavItem> {
  const items = new Map<string, NavItem>();
  for (const section of sections) {
    for (const item of section.items) items.set(item.key, item);
  }
  return items;
}

function defaultEditor(sections: NavSection[]): SidebarNavEditorState {
  const ungrouped: string[] = [];
  const groups: SidebarNavGroup[] = [];
  const itemsByGroup: Record<string, string[]> = {};
  for (const section of sections) {
    const keys = section.items.map((item) => item.key);
    if (!section.id && !section.groupKey && !section.title) {
      ungrouped.push(...keys);
      continue;
    }
    const id =
      section.id ??
      (section.groupKey ? BUILTIN_ID_BY_LABEL[section.groupKey] : undefined) ??
      section.groupKey ??
      "group";
    groups.push({ id, name: section.title ?? null });
    itemsByGroup[id] = keys;
  }
  return { groups, ungrouped, itemsByGroup, hidden: [] };
}

function defaultKeyOrder(state: SidebarNavEditorState): string[] {
  return [
    ...state.ungrouped,
    ...state.groups.flatMap((group) => state.itemsByGroup[group.id] ?? []),
  ];
}

/** Editor model for the drawer. A missing layout is the system default. */
export function editorFromCatalog(
  sections: NavSection[],
  layout: SidebarNavLayout | null,
): SidebarNavEditorState {
  const base = defaultEditor(sections);
  if (!layout) return base;

  const catalogKeys = new Set(defaultKeyOrder(base));
  const groups: SidebarNavGroup[] = [];
  const groupIds = new Set<string>();
  for (const group of layout.groups) {
    if (groupIds.has(group.id)) continue;
    groupIds.add(group.id);
    groups.push({ id: group.id, name: group.name ?? null });
  }
  const itemsByGroup: Record<string, string[]> = {};
  for (const group of groups) itemsByGroup[group.id] = [];

  const ungrouped: string[] = [];
  const hidden: string[] = [];
  const seen = new Set<string>();
  // New built-in groups that ship after the user saved a layout (e.g. a
  // freshly introduced "personalization" group) must be spliced back in —
  // ahead of the first existing built-in group — or their items would have
  // no parent group and end up hidden forever.
  const missingBuiltinGroups = BUILTIN_NAV_GROUP_IDS.filter(
    (id) => !groupIds.has(id),
  );
  if (missingBuiltinGroups.length > 0) {
    const firstBuiltinIdx = groups.findIndex((g) => isBuiltinNavGroupId(g.id));
    const inserted = missingBuiltinGroups.map((id) => ({
      id,
      name: null as string | null,
    }));
    if (firstBuiltinIdx === -1) {
      groups.push(...inserted);
    } else {
      groups.splice(firstBuiltinIdx, 0, ...inserted);
    }
    for (const g of inserted) {
      groupIds.add(g.id);
      itemsByGroup[g.id] = [];
    }
  }
  for (const item of layout.items) {
    if (!catalogKeys.has(item.key) || seen.has(item.key)) continue;
    seen.add(item.key);
    if (item.hidden) {
      hidden.push(item.key);
      continue;
    }
    if (item.group && groupIds.has(item.group)) {
      itemsByGroup[item.group].push(item.key);
    } else {
      ungrouped.push(item.key);
    }
  }
  // New built-in nav keys that ship after the user saved a layout would
  // otherwise be hidden forever. Append them to their default built-in
  // group (when that group still exists) instead of the hidden list.
  const defaultGroupIdByKey = new Map<string, string>();
  for (const group of base.groups) {
    for (const key of base.itemsByGroup[group.id] ?? []) {
      defaultGroupIdByKey.set(key, group.id);
    }
  }
  for (const key of defaultKeyOrder(base)) {
    if (seen.has(key)) continue;
    const defaultGroup = defaultGroupIdByKey.get(key);
    if (
      defaultGroup &&
      isBuiltinNavGroupId(defaultGroup) &&
      groupIds.has(defaultGroup)
    ) {
      seen.add(key);
      itemsByGroup[defaultGroup].push(key);
      continue;
    }
    hidden.push(key);
  }
  // Keys whose default built-in group changed (e.g. knowledge-bases moved
  // from "settings" to "personalization"): relocate saved-layout placements
  // into the new default group, keeping the base ordering inside it.
  // Keys the user manually hidden stay hidden. Keys that became ungrouped
  // (e.g. personalization-subagents moved to the top block) relocate into
  // the ungrouped list the same way.
  const layoutGroupByKey = new Map<string, string | null | undefined>();
  for (const item of layout.items) layoutGroupByKey.set(item.key, item.group);
  for (const key of defaultKeyOrder(base)) {
    if (!seen.has(key) || hidden.includes(key)) continue;
    const newDefault = defaultGroupIdByKey.get(key);
    const nowUngrouped = !newDefault;
    const savedGroup = layoutGroupByKey.get(key);
    const inUngroupedNow = ungrouped.includes(key);
    if (nowUngrouped) {
      if (!inUngroupedNow) {
        if (savedGroup && groupIds.has(savedGroup)) {
          itemsByGroup[savedGroup] = itemsByGroup[savedGroup].filter(
            (k) => k !== key,
          );
        }
        const baseOrder = defaultKeyOrder(base).filter((k) =>
          ungrouped.includes(k),
        );
        const baseIdx = baseOrder.indexOf(key);
        let insertAt = ungrouped.length;
        if (baseIdx !== -1) {
          for (let i = baseIdx + 1; i < baseOrder.length; i++) {
            const pos = ungrouped.indexOf(baseOrder[i]);
            if (pos !== -1) {
              insertAt = pos;
              break;
            }
          }
        }
        ungrouped.splice(insertAt, 0, key);
      }
      continue;
    }
    if (
      !isBuiltinNavGroupId(newDefault) ||
      !groupIds.has(newDefault)
    ) {
      continue;
    }
    const currentGroup = inUngroupedNow
      ? null
      : savedGroup && groupIds.has(savedGroup)
        ? savedGroup
        : undefined;
    if (currentGroup === newDefault) continue;
    // Remove from the old location (ungrouped or old group).
    if (inUngroupedNow) {
      ungrouped.splice(ungrouped.indexOf(key), 1);
    } else if (currentGroup) {
      itemsByGroup[currentGroup] = itemsByGroup[currentGroup].filter(
        (k) => k !== key,
      );
    }
    // Insert before the first base-order sibling that follows it in the
    // new group; fall back to appending at the group tail.
    const baseOrder = base.itemsByGroup[newDefault] ?? [];
    const baseIdx = baseOrder.indexOf(key);
    let insertAt = itemsByGroup[newDefault].length;
    if (baseIdx !== -1) {
      for (let i = baseIdx + 1; i < baseOrder.length; i++) {
        const pos = itemsByGroup[newDefault].indexOf(baseOrder[i]);
        if (pos !== -1) {
          insertAt = pos;
          break;
        }
      }
    }
    itemsByGroup[newDefault].splice(insertAt, 0, key);
  }
  return { groups, ungrouped, itemsByGroup, hidden };
}

/**
 * Groups to show in the customizer.
 * Built-in groups the user cannot access stay out. Empty custom groups stay,
 * so items can be dragged back in.
 */
export function visibleEditorGroups(
  state: SidebarNavEditorState,
  sections: NavSection[],
): SidebarNavGroup[] {
  const catalogGroupIds = new Set(
    sections.flatMap((section) => (section.id ? [section.id] : [])),
  );
  return state.groups.filter((group) => {
    const count = state.itemsByGroup[group.id]?.length ?? 0;
    if (count > 0) return true;
    if (!isBuiltinNavGroupId(group.id)) return true;
    return catalogGroupIds.has(group.id);
  });
}

/** Keys stored for items the current user cannot see, so a later save does not drop them. */
export function preservedPlacements(
  layout: SidebarNavLayout | null,
  sections: NavSection[],
): SidebarNavItemPlacement[] {
  if (!layout) return [];
  const visible = new Set(catalogItems(sections).keys());
  return layout.items.filter(
    (item) => NAV_KEY_SET.has(item.key) && !visible.has(item.key),
  );
}

export function layoutFromEditor(
  state: SidebarNavEditorState,
  preserved: SidebarNavItemPlacement[] = [],
): SidebarNavLayout {
  const items: SidebarNavItemPlacement[] = [];
  const seen = new Set<string>();
  const push = (item: SidebarNavItemPlacement) => {
    if (seen.has(item.key)) return;
    seen.add(item.key);
    items.push(item);
  };
  for (const key of state.ungrouped) push({ key });
  for (const group of state.groups) {
    for (const key of state.itemsByGroup[group.id] ?? []) {
      push({ key, group: group.id });
    }
  }
  for (const key of state.hidden) push({ key, hidden: true });
  for (const extra of preserved) push(extra);
  return {
    groups: state.groups.map((group) => {
      const name = group.name?.trim() ?? "";
      return name ? { id: group.id, name } : { id: group.id };
    }),
    items,
  };
}

function sectionForGroup(
  group: SidebarNavGroup,
  items: NavItem[],
): NavSection | null {
  if (items.length === 0) return null;
  const custom = group.name?.trim() ?? "";
  if (custom) return { id: group.id, title: custom, items };
  const labelKey = builtinNavGroupLabelKey(group.id);
  if (labelKey) return { id: group.id, groupKey: labelKey, items };
  return null;
}

/** Sidebar sections. Empty groups are omitted. `null` layout keeps the catalog. */
export function sectionsFromLayout(
  sections: NavSection[],
  layout: SidebarNavLayout | null,
): NavSection[] {
  if (!layout) return sections;
  const byKey = catalogItems(sections);
  const editor = editorFromCatalog(sections, layout);
  const result: NavSection[] = [];
  const ungrouped = editor.ungrouped
    .map((key) => byKey.get(key))
    .filter((item): item is NavItem => Boolean(item));
  if (ungrouped.length > 0) result.push({ items: ungrouped });
  for (const group of editor.groups) {
    const items = (editor.itemsByGroup[group.id] ?? [])
      .map((key) => byKey.get(key))
      .filter((item): item is NavItem => Boolean(item));
    const section = sectionForGroup(group, items);
    if (section) result.push(section);
  }
  return result;
}

function stripKey(
  state: SidebarNavEditorState,
  key: string,
): SidebarNavEditorState {
  const itemsByGroup: Record<string, string[]> = {};
  for (const [id, keys] of Object.entries(state.itemsByGroup)) {
    itemsByGroup[id] = keys.filter((item) => item !== key);
  }
  return {
    ...state,
    ungrouped: state.ungrouped.filter((item) => item !== key),
    hidden: state.hidden.filter((item) => item !== key),
    itemsByGroup,
  };
}

function zoneList(
  state: SidebarNavEditorState,
  zone: SidebarNavItemZone,
): string[] {
  if (zone.kind === "ungrouped") return state.ungrouped;
  if (zone.kind === "hidden") return state.hidden;
  return state.itemsByGroup[zone.groupId] ?? [];
}

function withZoneList(
  state: SidebarNavEditorState,
  zone: SidebarNavItemZone,
  list: string[],
): SidebarNavEditorState {
  if (zone.kind === "ungrouped") return { ...state, ungrouped: list };
  if (zone.kind === "hidden") return { ...state, hidden: list };
  return {
    ...state,
    itemsByGroup: { ...state.itemsByGroup, [zone.groupId]: list },
  };
}

/** Insert `key` before `beforeKey`. `beforeKey` null appends. */
export function placeItem(
  state: SidebarNavEditorState,
  key: string,
  zone: SidebarNavItemZone,
  beforeKey: string | null,
): SidebarNavEditorState {
  if (beforeKey === key) return state;
  if (
    zone.kind === "group" &&
    !state.groups.some((group) => group.id === zone.groupId)
  ) {
    return state;
  }
  const stripped = stripKey(state, key);
  const list = [...zoneList(stripped, zone)];
  const index = beforeKey ? list.indexOf(beforeKey) : list.length;
  list.splice(index < 0 ? list.length : index, 0, key);
  return withZoneList(stripped, zone, list);
}

export function moveGroup(
  state: SidebarNavEditorState,
  groupId: string,
  beforeId: string | null,
): SidebarNavEditorState {
  if (beforeId === groupId) return state;
  const moving = state.groups.find((group) => group.id === groupId);
  if (!moving) return state;
  const groups = state.groups.filter((group) => group.id !== groupId);
  const index = beforeId
    ? groups.findIndex((group) => group.id === beforeId)
    : groups.length;
  groups.splice(index < 0 ? groups.length : index, 0, moving);
  return { ...state, groups };
}

export function createGroup(
  state: SidebarNavEditorState,
  id: string,
  name: string,
): SidebarNavEditorState {
  return {
    ...state,
    groups: [...state.groups, { id, name }],
    itemsByGroup: { ...state.itemsByGroup, [id]: [] },
  };
}

export function renameGroup(
  state: SidebarNavEditorState,
  id: string,
  name: string | null,
): SidebarNavEditorState {
  return {
    ...state,
    groups: state.groups.map((group) =>
      group.id === id ? { ...group, name } : group,
    ),
  };
}

/** Drop the group. Its items become ungrouped and move to the front. */
export function deleteGroup(
  state: SidebarNavEditorState,
  groupId: string,
): SidebarNavEditorState {
  const released = state.itemsByGroup[groupId] ?? [];
  const itemsByGroup = { ...state.itemsByGroup };
  delete itemsByGroup[groupId];
  return {
    ...state,
    groups: state.groups.filter((group) => group.id !== groupId),
    ungrouped: [...released, ...state.ungrouped],
    itemsByGroup,
  };
}

export function nextGroupName(
  state: SidebarNavEditorState,
  base: string,
): string {
  const names = new Set(
    state.groups.map((group) => (group.name ?? "").trim()).filter(Boolean),
  );
  if (!names.has(base)) return base;
  let n = 2;
  while (names.has(`${base} ${n}`)) n += 1;
  return `${base} ${n}`;
}

export function newNavGroupId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  const body = Array.from(bytes, (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return `c_${body}`;
}

export function groupNameMissing(state: SidebarNavEditorState): boolean {
  return state.groups.some((group) => {
    if (isBuiltinNavGroupId(group.id)) return false;
    return !(group.name ?? "").trim();
  });
}
