import { countWords, estimateSeconds, formatClock, isYouTubeUrl, parseTimestamp, slugify, youtubeAt } from "../lib/format";

describe("format", () => {
  it("formats the tape counter", () => {
    expect(formatClock(0)).toBe("00:00");
    expect(formatClock(292)).toBe("04:52");
    expect(formatClock(3725)).toBe("1:02:05");
    expect(formatClock(Number.NaN)).toBe("00:00");
  });
  it("parses timestamps", () => {
    expect(parseTimestamp("01:15")).toBe(75);
    expect(parseTimestamp("1:02:05")).toBe(3725);
    expect(parseTimestamp("x")).toBeNull();
    expect(parseTimestamp(undefined)).toBeNull();
  });
  it("counts words and estimates duration at 150 wpm", () => {
    expect(countWords("  um  dois\ntrês ")).toBe(3);
    expect(countWords("")).toBe(0);
    expect(estimateSeconds(750)).toBe(300);
  });
  it("builds youtube links at a timestamp", () => {
    expect(youtubeAt("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "01:15")).toBe(
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=75s",
    );
    expect(youtubeAt("https://youtu.be/dQw4w9WgXcQ", "00:05")).toBe("https://youtu.be/dQw4w9WgXcQ?t=5s");
    expect(youtubeAt(null, "00:05")).toBeNull();
  });
  it("validates youtube urls", () => {
    expect(isYouTubeUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")).toBe(true);
    expect(isYouTubeUrl("youtu.be/dQw4w9WgXcQ")).toBe(true);
    expect(isYouTubeUrl("https://youtube.com/shorts/dQw4w9WgXcQ")).toBe(true);
    expect(isYouTubeUrl("https://evil.com/watch?v=dQw4w9WgXcQ")).toBe(false);
  });
  it("slugifies titles", () => {
    expect(slugify("Exame: Café & Saúde!")).toBe("exame-cafe-saude");
    expect(slugify("!!!")).toBe("episodio");
  });
});
