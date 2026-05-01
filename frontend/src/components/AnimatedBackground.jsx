/**
 * AnimatedBackground — Global ambient animated background.
 * Renders floating gradient orbs, rising particles, and a subtle grid mesh.
 * Styles live in App.css so they load once for the entire app.
 */
export default function AnimatedBackground() {
  return (
    <div className="animated-bg" aria-hidden="true">
      {/* Gradient orbs */}
      <div className="animated-bg__orb animated-bg__orb--1" />
      <div className="animated-bg__orb animated-bg__orb--2" />
      <div className="animated-bg__orb animated-bg__orb--3" />
      <div className="animated-bg__orb animated-bg__orb--4" />

      {/* Rising particles */}
      <div className="animated-bg__particles">
        {[...Array(12)].map((_, i) => (
          <div key={i} className="animated-bg__particle" />
        ))}
      </div>

      {/* Grid mesh overlay */}
      <div className="animated-bg__mesh" />
    </div>
  );
}
