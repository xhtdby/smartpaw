import type { ActionCard, AnalysisContext, ChatMessage } from "@/lib/api";

export type ThreadKind = "general" | "image";

export interface StoredChatMessage extends ChatMessage {
  action_cards?: ActionCard[];
  is_emergency?: boolean;
}

export interface ChatThread {
  id: string;
  kind: ThreadKind;
  image_id?: string;
  created_at: string;
  last_used_at: string;
  messages: StoredChatMessage[];
  analysis_context?: AnalysisContext | string;
}

export interface ImageRecord {
  id: string;
  blob: Blob;
  thumbnail_blob: Blob;
  created_at: string;
  analysis_status: string;
  analysis_context?: AnalysisContext;
}

export interface ThreadIndexItem {
  id: string;
  kind: ThreadKind;
  image_id?: string;
  created_at: string;
  last_used_at: string;
  title: string;
  thumbnail_data_url?: string;
}

const DB_NAME = "indieaid-client-store";
const DB_VERSION = 1;
const THREAD_STORE = "chat_threads";
const IMAGE_STORE = "image_records";
const THREAD_INDEX_KEY = "indieaid-thread-index";
const ACTIVE_THREAD_KEY = "indieaid-active-thread-id";
const MIGRATION_KEY = "indieaid-thread-migration-v1";
const GENERAL_THREAD_ID = "general";
const MAX_IMAGE_THREADS = 12;
const MAX_MESSAGES_PER_THREAD = 60;
const STORED_IMAGE_MAX_EDGE = 960;
const STORED_IMAGE_TARGET_BYTES = 240 * 1024;
const STORED_THUMBNAIL_MAX_EDGE = 128;
const STORED_THUMBNAIL_TARGET_BYTES = 24 * 1024;

const LEGACY_CHAT_KEYS = ["indieaid-chat-history", "smartpaw-chat-history"];
const LEGACY_ANALYSIS_KEYS = ["indieaid-analysis-context", "smartpaw-analysis-context"];

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof indexedDB !== "undefined";
}

function nowIso(): string {
  return new Date().toISOString();
}

function makeId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}_${crypto.randomUUID()}`;
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!isBrowser()) {
      reject(new Error("IndexedDB is not available"));
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(THREAD_STORE)) db.createObjectStore(THREAD_STORE);
      if (!db.objectStoreNames.contains(IMAGE_STORE)) db.createObjectStore(IMAGE_STORE);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Could not open IndexedDB"));
  });
}

async function idbGet<T>(storeName: string, key: string): Promise<T | undefined> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const request = db.transaction(storeName, "readonly").objectStore(storeName).get(key);
    request.onsuccess = () => resolve(request.result as T | undefined);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB read failed"));
  });
}

async function idbSet<T>(storeName: string, key: string, value: T): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const request = db.transaction(storeName, "readwrite").objectStore(storeName).put(value, key);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error ?? new Error("IndexedDB write failed"));
  });
}

async function idbDelete(storeName: string, key: string): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const request = db.transaction(storeName, "readwrite").objectStore(storeName).delete(key);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error ?? new Error("IndexedDB delete failed"));
  });
}

async function idbClear(storeName: string): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const request = db.transaction(storeName, "readwrite").objectStore(storeName).clear();
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error ?? new Error("IndexedDB clear failed"));
  });
}

export function readThreadIndex(): ThreadIndexItem[] {
  if (!isBrowser()) return [];
  try {
    const raw = localStorage.getItem(THREAD_INDEX_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeThreadIndex(index: ThreadIndexItem[]): ThreadIndexItem[] {
  const sorted = [...index].sort((a, b) => b.last_used_at.localeCompare(a.last_used_at));
  localStorage.setItem(THREAD_INDEX_KEY, JSON.stringify(sorted));
  return sorted;
}

function threadTitle(thread: ChatThread): string {
  if (thread.kind === "general") return "General";
  const firstUserMessage = thread.messages.find((message) => message.role === "user")?.content;
  if (firstUserMessage) {
    return firstUserMessage.length > 32 ? `${firstUserMessage.slice(0, 31)}...` : firstUserMessage;
  }
  return "Photo thread";
}

function updateIndexForThread(
  thread: ChatThread,
  currentIndex: ThreadIndexItem[],
  thumbnailDataUrl?: string
): ThreadIndexItem[] {
  const existing = currentIndex.find((item) => item.id === thread.id);
  const nextItem: ThreadIndexItem = {
    id: thread.id,
    kind: thread.kind,
    image_id: thread.image_id,
    created_at: thread.created_at,
    last_used_at: thread.last_used_at,
    title: threadTitle(thread),
    thumbnail_data_url: thumbnailDataUrl ?? existing?.thumbnail_data_url,
  };
  return writeThreadIndex([nextItem, ...currentIndex.filter((item) => item.id !== thread.id)]);
}

function parseLegacyAnalysis(): AnalysisContext | string | undefined {
  for (const key of LEGACY_ANALYSIS_KEYS) {
    const raw = localStorage.getItem(key);
    if (!raw) continue;
    try {
      return JSON.parse(raw) as AnalysisContext;
    } catch {
      return raw;
    }
  }
  return undefined;
}

function parseLegacyMessages(): StoredChatMessage[] {
  for (const key of LEGACY_CHAT_KEYS) {
    const raw = localStorage.getItem(key);
    if (!raw) continue;
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

function removeLegacyKeys(): void {
  for (const key of [...LEGACY_CHAT_KEYS, ...LEGACY_ANALYSIS_KEYS]) {
    localStorage.removeItem(key);
  }
}

async function migrateLegacyStorage(): Promise<void> {
  if (localStorage.getItem(MIGRATION_KEY)) return;

  const messages = parseLegacyMessages();
  const analysisContext = parseLegacyAnalysis();
  if (messages.length || analysisContext) {
    const timestamp = nowIso();
    await idbSet<ChatThread>(THREAD_STORE, GENERAL_THREAD_ID, {
      id: GENERAL_THREAD_ID,
      kind: "general",
      created_at: timestamp,
      last_used_at: timestamp,
      messages,
      analysis_context: analysisContext,
    });
    updateIndexForThread(
      {
        id: GENERAL_THREAD_ID,
        kind: "general",
        created_at: timestamp,
        last_used_at: timestamp,
        messages,
        analysis_context: analysisContext,
      },
      []
    );
  }

  removeLegacyKeys();
  localStorage.setItem(MIGRATION_KEY, "1");
}

export async function initializeThreadStore(): Promise<ThreadIndexItem[]> {
  if (!isBrowser()) return [];
  await migrateLegacyStorage();

  let index = readThreadIndex();
  const hasGeneral = index.some((item) => item.id === GENERAL_THREAD_ID);
  if (!hasGeneral) {
    const timestamp = nowIso();
    const generalThread: ChatThread = {
      id: GENERAL_THREAD_ID,
      kind: "general",
      created_at: timestamp,
      last_used_at: timestamp,
      messages: [],
    };
    await idbSet(THREAD_STORE, GENERAL_THREAD_ID, generalThread);
    index = updateIndexForThread(generalThread, index);
  }

  return index;
}

export async function getThread(threadId: string): Promise<ChatThread | undefined> {
  if (!isBrowser()) return undefined;
  return idbGet<ChatThread>(THREAD_STORE, threadId);
}

export async function saveThread(thread: ChatThread): Promise<ThreadIndexItem[]> {
  if (!isBrowser()) return [];
  const trimmed: ChatThread = {
    ...thread,
    messages: thread.messages.slice(-MAX_MESSAGES_PER_THREAD),
    last_used_at: nowIso(),
  };
  await idbSet(THREAD_STORE, trimmed.id, trimmed);
  return updateIndexForThread(trimmed, readThreadIndex());
}

export async function saveThreadContext(
  thread: ChatThread,
  analysisContext?: AnalysisContext | string
): Promise<ThreadIndexItem[]> {
  return saveThread({ ...thread, analysis_context: analysisContext });
}

export function getActiveThreadId(): string {
  if (!isBrowser()) return GENERAL_THREAD_ID;
  return localStorage.getItem(ACTIVE_THREAD_KEY) || GENERAL_THREAD_ID;
}

export function setActiveThreadId(threadId: string): void {
  if (!isBrowser()) return;
  localStorage.setItem(ACTIVE_THREAD_KEY, threadId);
}

async function canvasToBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error("Could not encode image"));
      },
      "image/jpeg",
      quality
    );
  });
}

async function loadImage(blob: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not load image"));
    };
    image.src = url;
  });
}

async function resizeToJpeg(
  blob: Blob,
  maxEdge: number,
  quality: number,
  targetBytes: number
): Promise<Blob> {
  const image = await loadImage(blob);
  const edgeCandidates = Array.from(new Set([maxEdge, 840, 720, 640, 480].filter((edge) => edge > 0)));
  const qualityCandidates = Array.from(
    new Set([quality, 0.62, 0.56, 0.5, 0.45].filter((value) => value > 0 && value <= 1))
  );
  let smallest: Blob | undefined;

  for (const edge of edgeCandidates) {
    const scale = Math.min(1, edge / Math.max(image.naturalWidth, image.naturalHeight));
    const width = Math.max(1, Math.round(image.naturalWidth * scale));
    const height = Math.max(1, Math.round(image.naturalHeight * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Canvas is not available");
    context.drawImage(image, 0, 0, width, height);

    for (const nextQuality of qualityCandidates) {
      const encoded = await canvasToBlob(canvas, nextQuality);
      if (!smallest || encoded.size < smallest.size) smallest = encoded;
      if (encoded.size <= targetBytes) return encoded;
    }
  }

  if (!smallest) throw new Error("Could not encode image");
  return smallest;
}

async function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Could not read blob"));
    reader.readAsDataURL(blob);
  });
}

async function enforceThreadCap(): Promise<void> {
  const index = readThreadIndex();
  const imageThreads = index
    .filter((item) => item.kind === "image")
    .sort((a, b) => b.last_used_at.localeCompare(a.last_used_at));
  const keepImageIds = new Set(imageThreads.slice(0, MAX_IMAGE_THREADS).map((item) => item.id));
  const evicted = imageThreads.slice(MAX_IMAGE_THREADS);

  for (const item of evicted) {
    await idbDelete(THREAD_STORE, item.id);
    if (item.image_id) await idbDelete(IMAGE_STORE, item.image_id);
  }

  if (evicted.length) {
    writeThreadIndex(index.filter((item) => item.kind !== "image" || keepImageIds.has(item.id)));
  }
}

export async function createImageThreadFromAnalysis(
  file: File,
  analysisContext: AnalysisContext,
  analysisStatus: string = "complete"
): Promise<string> {
  if (!isBrowser()) throw new Error("Browser storage is not available");

  const timestamp = nowIso();
  const imageId = makeId("image");
  const threadId = makeId("thread");
  const [blob, thumbnailBlob] = await Promise.all([
    resizeToJpeg(file, STORED_IMAGE_MAX_EDGE, 0.68, STORED_IMAGE_TARGET_BYTES),
    resizeToJpeg(file, STORED_THUMBNAIL_MAX_EDGE, 0.6, STORED_THUMBNAIL_TARGET_BYTES),
  ]);
  const thumbnailDataUrl = await blobToDataUrl(thumbnailBlob);

  const imageRecord: ImageRecord = {
    id: imageId,
    blob,
    thumbnail_blob: thumbnailBlob,
    created_at: timestamp,
    analysis_status: analysisStatus,
    analysis_context: analysisContext,
  };
  const thread: ChatThread = {
    id: threadId,
    kind: "image",
    image_id: imageId,
    created_at: timestamp,
    last_used_at: timestamp,
    messages: [],
    analysis_context: analysisContext,
  };

  await idbSet(IMAGE_STORE, imageId, imageRecord);
  await idbSet(THREAD_STORE, threadId, thread);
  updateIndexForThread(thread, readThreadIndex(), thumbnailDataUrl);
  setActiveThreadId(threadId);
  await enforceThreadCap();

  return threadId;
}

export async function clearThread(threadId: string): Promise<ThreadIndexItem[]> {
  const existing = await getThread(threadId);
  if (!existing) return readThreadIndex();
  const cleared: ChatThread = {
    ...existing,
    messages: [],
    analysis_context: undefined,
    last_used_at: nowIso(),
  };
  await idbSet(THREAD_STORE, threadId, cleared);
  return updateIndexForThread(cleared, readThreadIndex());
}

export async function clearAllThreadStorage(): Promise<ThreadIndexItem[]> {
  if (!isBrowser()) return [];
  await Promise.all([idbClear(THREAD_STORE), idbClear(IMAGE_STORE)]);
  localStorage.removeItem(THREAD_INDEX_KEY);
  localStorage.removeItem(ACTIVE_THREAD_KEY);
  localStorage.removeItem(MIGRATION_KEY);
  removeLegacyKeys();
  return initializeThreadStore();
}

export { GENERAL_THREAD_ID };
