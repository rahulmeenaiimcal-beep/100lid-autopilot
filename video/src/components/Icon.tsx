import React from "react";
import * as Lucide from "lucide-react";

// Simple names the script writer may use -> Lucide icon names (ISC licence).
// Looked up at run time with a safe fallback, so a renamed icon can never break a render.
export const ICONS: Record<string, string[]> = {
  bank: ["Landmark"],
  building: ["Building2", "Building"],
  card: ["CreditCard"],
  phone: ["Smartphone"],
  document: ["FileText"],
  form: ["ClipboardList", "FileText"],
  passbook: ["BookOpen"],
  book: ["BookOpen"],
  piggybank: ["PiggyBank"],
  wallet: ["Wallet"],
  coins: ["Coins"],
  cash: ["Banknote"],
  rupee: ["IndianRupee"],
  home: ["House", "Home"],
  tractor: ["Tractor"],
  wheat: ["Wheat"],
  farm: ["Sprout"],
  shop: ["Store"],
  factory: ["Factory"],
  education: ["GraduationCap"],
  school: ["School"],
  baby: ["Baby"],
  girl: ["User"],
  health: ["HeartPulse"],
  hospital: ["Hospital", "HeartPulse"],
  insurance: ["ShieldCheck"],
  shield: ["Shield"],
  law: ["Scale"],
  court: ["Gavel"],
  calendar: ["Calendar"],
  percent: ["Percent"],
  growth: ["TrendingUp"],
  fall: ["TrendingDown"],
  people: ["Users"],
  person: ["User"],
  aadhaar: ["Fingerprint"],
  fingerprint: ["Fingerprint"],
  qr: ["QrCode"],
  upi: ["QrCode"],
  receipt: ["Receipt"],
  loan: ["HandCoins", "Coins"],
  business: ["Briefcase"],
  lock: ["Lock"],
  key: ["Key"],
  target: ["Target"],
  clock: ["Clock"],
  location: ["MapPin"],
  award: ["Award"],
  idea: ["Lightbulb"],
  gift: ["Gift"],
  truck: ["Truck"],
  leaf: ["Leaf"],
  umbrella: ["Umbrella"],
  doctor: ["Stethoscope"],
  tools: ["Hammer", "Wrench"],
  cart: ["ShoppingCart"],
  package: ["Package"],
  calculator: ["Calculator"],
  chart: ["ChartColumn", "BarChart3", "BarChart"],
  globe: ["Globe"],
  mail: ["Mail"],
  star: ["Star"],
  heart: ["Heart"],
  water: ["Droplets"],
  energy: ["Zap"],
  sun: ["Sun"],
  flag: ["Flag"],
  check: ["CircleCheck", "CheckCircle"],
  warning: ["TriangleAlert", "AlertTriangle"],
  question: ["CircleHelp", "HelpCircle"],
  photo: ["Camera"],
  signature: ["PenLine", "PenTool"],
  government: ["Landmark"],
  village: ["Tent", "House"],
  woman: ["User"],
  senior: ["User"],
  car: ["Car"],
  plane: ["Plane"],
};

export const iconComponent = (name?: string): React.FC<any> => {
  const lib = Lucide as unknown as Record<string, React.FC<any>>;
  const key = (name || "").toLowerCase().trim();
  const candidates = ICONS[key] || [name || ""];
  for (const c of candidates) {
    if (lib[c]) return lib[c];
  }
  return lib["Circle"] || (() => null);
};

export const Icon: React.FC<{ name?: string; size: number; color?: string; stroke?: number }> = ({
  name,
  size,
  color = "#1d2433",
  stroke = 2,
}) => {
  const Comp = iconComponent(name);
  return <Comp size={size} color={color} strokeWidth={stroke} />;
};
