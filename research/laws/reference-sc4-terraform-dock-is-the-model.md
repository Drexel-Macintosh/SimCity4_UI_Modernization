---
name: reference-sc4-terraform-dock-is-the-model
description: "SC4 god flyouts: TERRAFORM's ring-on-button-1 is the CORRECT reference; Disaster must ring button 4 the same way"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-25T02:03:30.351Z
---

For the SC4 god-mode flyout scaling work, **TERRAFORM (button 1, green) is the
gold-standard reference**: its coloured ring/connector-arm wraps its own spawn
button correctly, and the flyout column joins to it cleanly. User confirmed this
repeatedly (2026-07-25) and said explicitly: *this is exactly what DISASTER
(button 4, orange, tornado) must do* — the orange flyout/ring must sit on button
4 the way terraform's sits on button 1.

The defect: the disaster flyout floats too HIGH (arm points at ~button-2/3
level) and must move DOWN + slightly LEFT onto button 4. Compare-to-terraform is
the acceptance test the user uses.

Derived dock (matches the working terrain-fx method, NOT eyeballed):
- toolbar `0xC991EDA8` abs `(10,422)`, 120px button pitch at 2x →
  **button 4 centre = (104, 860)**.
- terrain-fx docks `(22,502)`, arm lands on button 2 centre `620` → arm sits
  **118px below the flyout top**.
- ⇒ disaster flyout top = 860 − 118 = **742**, same left column X=22 ⇒ toolbar
  offset **(6, 160)**. Vector from the raw (126,518) undocked pos = down 224,
  left 104 (mostly down, some left — matches the user's drawn arrow).

Related: [[project-sc4-god-flyouts]], [[feedback-sc4-regression-net]]
