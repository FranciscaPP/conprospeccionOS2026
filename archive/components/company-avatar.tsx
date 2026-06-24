interface CompanyAvatarProps {
  name: string;
  size?: number;
}

const PALETTE = ["#333333", "#0e9f6e", "#b06a00", "#7a7a72", "#c0362c"];

function getInitials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function hashString(str: string) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export function CompanyAvatar({ name, size = 26 }: CompanyAvatarProps) {
  const bg = PALETTE[hashString(name) % PALETTE.length];
  return (
    <div
      className="font-display tnum"
      style={{
        width: size,
        height: size,
        borderRadius: 7,
        background: bg,
        color: "#fff",
        display: "grid",
        placeItems: "center",
        fontWeight: 700,
        fontSize: Math.round(size * 0.4),
        flexShrink: 0,
        lineHeight: 1,
      }}
      aria-hidden
    >
      {getInitials(name)}
    </div>
  );
}
