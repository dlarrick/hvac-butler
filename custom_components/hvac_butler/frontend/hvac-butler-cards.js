/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var _a;
const t$2 = globalThis, e$2 = t$2.ShadowRoot && (void 0 === t$2.ShadyCSS || t$2.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, s$2 = Symbol(), o$4 = /* @__PURE__ */ new WeakMap();
let n$3 = class n {
  constructor(t2, e2, o2) {
    if (this._$cssResult$ = true, o2 !== s$2) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t2, this.t = e2;
  }
  get styleSheet() {
    let t2 = this.o;
    const s2 = this.t;
    if (e$2 && void 0 === t2) {
      const e2 = void 0 !== s2 && 1 === s2.length;
      e2 && (t2 = o$4.get(s2)), void 0 === t2 && ((this.o = t2 = new CSSStyleSheet()).replaceSync(this.cssText), e2 && o$4.set(s2, t2));
    }
    return t2;
  }
  toString() {
    return this.cssText;
  }
};
const r$4 = (t2) => new n$3("string" == typeof t2 ? t2 : t2 + "", void 0, s$2), i$3 = (t2, ...e2) => {
  const o2 = 1 === t2.length ? t2[0] : e2.reduce((e3, s2, o3) => e3 + ((t3) => {
    if (true === t3._$cssResult$) return t3.cssText;
    if ("number" == typeof t3) return t3;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + t3 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s2) + t2[o3 + 1], t2[0]);
  return new n$3(o2, t2, s$2);
}, S$1 = (s2, o2) => {
  if (e$2) s2.adoptedStyleSheets = o2.map((t2) => t2 instanceof CSSStyleSheet ? t2 : t2.styleSheet);
  else for (const e2 of o2) {
    const o3 = document.createElement("style"), n3 = t$2.litNonce;
    void 0 !== n3 && o3.setAttribute("nonce", n3), o3.textContent = e2.cssText, s2.appendChild(o3);
  }
}, c$2 = e$2 ? (t2) => t2 : (t2) => t2 instanceof CSSStyleSheet ? ((t3) => {
  let e2 = "";
  for (const s2 of t3.cssRules) e2 += s2.cssText;
  return r$4(e2);
})(t2) : t2;
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const { is: i$2, defineProperty: e$1, getOwnPropertyDescriptor: h$1, getOwnPropertyNames: r$3, getOwnPropertySymbols: o$3, getPrototypeOf: n$2 } = Object, a$1 = globalThis, c$1 = a$1.trustedTypes, l$1 = c$1 ? c$1.emptyScript : "", p$1 = a$1.reactiveElementPolyfillSupport, d$1 = (t2, s2) => t2, u$1 = { toAttribute(t2, s2) {
  switch (s2) {
    case Boolean:
      t2 = t2 ? l$1 : null;
      break;
    case Object:
    case Array:
      t2 = null == t2 ? t2 : JSON.stringify(t2);
  }
  return t2;
}, fromAttribute(t2, s2) {
  let i2 = t2;
  switch (s2) {
    case Boolean:
      i2 = null !== t2;
      break;
    case Number:
      i2 = null === t2 ? null : Number(t2);
      break;
    case Object:
    case Array:
      try {
        i2 = JSON.parse(t2);
      } catch (t3) {
        i2 = null;
      }
  }
  return i2;
} }, f$1 = (t2, s2) => !i$2(t2, s2), b$1 = { attribute: true, type: String, converter: u$1, reflect: false, useDefault: false, hasChanged: f$1 };
Symbol.metadata ?? (Symbol.metadata = Symbol("metadata")), a$1.litPropertyMetadata ?? (a$1.litPropertyMetadata = /* @__PURE__ */ new WeakMap());
let y$1 = class y extends HTMLElement {
  static addInitializer(t2) {
    this._$Ei(), (this.l ?? (this.l = [])).push(t2);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t2, s2 = b$1) {
    if (s2.state && (s2.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t2) && ((s2 = Object.create(s2)).wrapped = true), this.elementProperties.set(t2, s2), !s2.noAccessor) {
      const i2 = Symbol(), h2 = this.getPropertyDescriptor(t2, i2, s2);
      void 0 !== h2 && e$1(this.prototype, t2, h2);
    }
  }
  static getPropertyDescriptor(t2, s2, i2) {
    const { get: e2, set: r2 } = h$1(this.prototype, t2) ?? { get() {
      return this[s2];
    }, set(t3) {
      this[s2] = t3;
    } };
    return { get: e2, set(s3) {
      const h2 = e2 == null ? void 0 : e2.call(this);
      r2 == null ? void 0 : r2.call(this, s3), this.requestUpdate(t2, h2, i2);
    }, configurable: true, enumerable: true };
  }
  static getPropertyOptions(t2) {
    return this.elementProperties.get(t2) ?? b$1;
  }
  static _$Ei() {
    if (this.hasOwnProperty(d$1("elementProperties"))) return;
    const t2 = n$2(this);
    t2.finalize(), void 0 !== t2.l && (this.l = [...t2.l]), this.elementProperties = new Map(t2.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(d$1("finalized"))) return;
    if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d$1("properties"))) {
      const t3 = this.properties, s2 = [...r$3(t3), ...o$3(t3)];
      for (const i2 of s2) this.createProperty(i2, t3[i2]);
    }
    const t2 = this[Symbol.metadata];
    if (null !== t2) {
      const s2 = litPropertyMetadata.get(t2);
      if (void 0 !== s2) for (const [t3, i2] of s2) this.elementProperties.set(t3, i2);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t3, s2] of this.elementProperties) {
      const i2 = this._$Eu(t3, s2);
      void 0 !== i2 && this._$Eh.set(i2, t3);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(s2) {
    const i2 = [];
    if (Array.isArray(s2)) {
      const e2 = new Set(s2.flat(1 / 0).reverse());
      for (const s3 of e2) i2.unshift(c$2(s3));
    } else void 0 !== s2 && i2.push(c$2(s2));
    return i2;
  }
  static _$Eu(t2, s2) {
    const i2 = s2.attribute;
    return false === i2 ? void 0 : "string" == typeof i2 ? i2 : "string" == typeof t2 ? t2.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    var _a2;
    this._$ES = new Promise((t2) => this.enableUpdating = t2), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), (_a2 = this.constructor.l) == null ? void 0 : _a2.forEach((t2) => t2(this));
  }
  addController(t2) {
    var _a2;
    (this._$EO ?? (this._$EO = /* @__PURE__ */ new Set())).add(t2), void 0 !== this.renderRoot && this.isConnected && ((_a2 = t2.hostConnected) == null ? void 0 : _a2.call(t2));
  }
  removeController(t2) {
    var _a2;
    (_a2 = this._$EO) == null ? void 0 : _a2.delete(t2);
  }
  _$E_() {
    const t2 = /* @__PURE__ */ new Map(), s2 = this.constructor.elementProperties;
    for (const i2 of s2.keys()) this.hasOwnProperty(i2) && (t2.set(i2, this[i2]), delete this[i2]);
    t2.size > 0 && (this._$Ep = t2);
  }
  createRenderRoot() {
    const t2 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return S$1(t2, this.constructor.elementStyles), t2;
  }
  connectedCallback() {
    var _a2;
    this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this.enableUpdating(true), (_a2 = this._$EO) == null ? void 0 : _a2.forEach((t2) => {
      var _a3;
      return (_a3 = t2.hostConnected) == null ? void 0 : _a3.call(t2);
    });
  }
  enableUpdating(t2) {
  }
  disconnectedCallback() {
    var _a2;
    (_a2 = this._$EO) == null ? void 0 : _a2.forEach((t2) => {
      var _a3;
      return (_a3 = t2.hostDisconnected) == null ? void 0 : _a3.call(t2);
    });
  }
  attributeChangedCallback(t2, s2, i2) {
    this._$AK(t2, i2);
  }
  _$ET(t2, s2) {
    var _a2;
    const i2 = this.constructor.elementProperties.get(t2), e2 = this.constructor._$Eu(t2, i2);
    if (void 0 !== e2 && true === i2.reflect) {
      const h2 = (void 0 !== ((_a2 = i2.converter) == null ? void 0 : _a2.toAttribute) ? i2.converter : u$1).toAttribute(s2, i2.type);
      this._$Em = t2, null == h2 ? this.removeAttribute(e2) : this.setAttribute(e2, h2), this._$Em = null;
    }
  }
  _$AK(t2, s2) {
    var _a2, _b;
    const i2 = this.constructor, e2 = i2._$Eh.get(t2);
    if (void 0 !== e2 && this._$Em !== e2) {
      const t3 = i2.getPropertyOptions(e2), h2 = "function" == typeof t3.converter ? { fromAttribute: t3.converter } : void 0 !== ((_a2 = t3.converter) == null ? void 0 : _a2.fromAttribute) ? t3.converter : u$1;
      this._$Em = e2;
      const r2 = h2.fromAttribute(s2, t3.type);
      this[e2] = r2 ?? ((_b = this._$Ej) == null ? void 0 : _b.get(e2)) ?? r2, this._$Em = null;
    }
  }
  requestUpdate(t2, s2, i2, e2 = false, h2) {
    var _a2;
    if (void 0 !== t2) {
      const r2 = this.constructor;
      if (false === e2 && (h2 = this[t2]), i2 ?? (i2 = r2.getPropertyOptions(t2)), !((i2.hasChanged ?? f$1)(h2, s2) || i2.useDefault && i2.reflect && h2 === ((_a2 = this._$Ej) == null ? void 0 : _a2.get(t2)) && !this.hasAttribute(r2._$Eu(t2, i2)))) return;
      this.C(t2, s2, i2);
    }
    false === this.isUpdatePending && (this._$ES = this._$EP());
  }
  C(t2, s2, { useDefault: i2, reflect: e2, wrapped: h2 }, r2) {
    i2 && !(this._$Ej ?? (this._$Ej = /* @__PURE__ */ new Map())).has(t2) && (this._$Ej.set(t2, r2 ?? s2 ?? this[t2]), true !== h2 || void 0 !== r2) || (this._$AL.has(t2) || (this.hasUpdated || i2 || (s2 = void 0), this._$AL.set(t2, s2)), true === e2 && this._$Em !== t2 && (this._$Eq ?? (this._$Eq = /* @__PURE__ */ new Set())).add(t2));
  }
  async _$EP() {
    this.isUpdatePending = true;
    try {
      await this._$ES;
    } catch (t3) {
      Promise.reject(t3);
    }
    const t2 = this.scheduleUpdate();
    return null != t2 && await t2, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    var _a2;
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ?? (this.renderRoot = this.createRenderRoot()), this._$Ep) {
        for (const [t4, s3] of this._$Ep) this[t4] = s3;
        this._$Ep = void 0;
      }
      const t3 = this.constructor.elementProperties;
      if (t3.size > 0) for (const [s3, i2] of t3) {
        const { wrapped: t4 } = i2, e2 = this[s3];
        true !== t4 || this._$AL.has(s3) || void 0 === e2 || this.C(s3, void 0, i2, e2);
      }
    }
    let t2 = false;
    const s2 = this._$AL;
    try {
      t2 = this.shouldUpdate(s2), t2 ? (this.willUpdate(s2), (_a2 = this._$EO) == null ? void 0 : _a2.forEach((t3) => {
        var _a3;
        return (_a3 = t3.hostUpdate) == null ? void 0 : _a3.call(t3);
      }), this.update(s2)) : this._$EM();
    } catch (s3) {
      throw t2 = false, this._$EM(), s3;
    }
    t2 && this._$AE(s2);
  }
  willUpdate(t2) {
  }
  _$AE(t2) {
    var _a2;
    (_a2 = this._$EO) == null ? void 0 : _a2.forEach((t3) => {
      var _a3;
      return (_a3 = t3.hostUpdated) == null ? void 0 : _a3.call(t3);
    }), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t2)), this.updated(t2);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t2) {
    return true;
  }
  update(t2) {
    this._$Eq && (this._$Eq = this._$Eq.forEach((t3) => this._$ET(t3, this[t3]))), this._$EM();
  }
  updated(t2) {
  }
  firstUpdated(t2) {
  }
};
y$1.elementStyles = [], y$1.shadowRootOptions = { mode: "open" }, y$1[d$1("elementProperties")] = /* @__PURE__ */ new Map(), y$1[d$1("finalized")] = /* @__PURE__ */ new Map(), p$1 == null ? void 0 : p$1({ ReactiveElement: y$1 }), (a$1.reactiveElementVersions ?? (a$1.reactiveElementVersions = [])).push("2.1.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t$1 = globalThis, i$1 = (t2) => t2, s$1 = t$1.trustedTypes, e = s$1 ? s$1.createPolicy("lit-html", { createHTML: (t2) => t2 }) : void 0, h = "$lit$", o$2 = `lit$${Math.random().toFixed(9).slice(2)}$`, n$1 = "?" + o$2, r$2 = `<${n$1}>`, l = document, c = () => l.createComment(""), a = (t2) => null === t2 || "object" != typeof t2 && "function" != typeof t2, u = Array.isArray, d = (t2) => u(t2) || "function" == typeof (t2 == null ? void 0 : t2[Symbol.iterator]), f = "[ 	\n\f\r]", v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, _ = /-->/g, m = />/g, p = RegExp(`>|${f}(?:([^\\s"'>=/]+)(${f}*=${f}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), g = /'/g, $ = /"/g, y2 = /^(?:script|style|textarea|title)$/i, x = (t2) => (i2, ...s2) => ({ _$litType$: t2, strings: i2, values: s2 }), b = x(1), E = Symbol.for("lit-noChange"), A = Symbol.for("lit-nothing"), C = /* @__PURE__ */ new WeakMap(), P = l.createTreeWalker(l, 129);
function V(t2, i2) {
  if (!u(t2) || !t2.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return void 0 !== e ? e.createHTML(i2) : i2;
}
const N = (t2, i2) => {
  const s2 = t2.length - 1, e2 = [];
  let n3, l2 = 2 === i2 ? "<svg>" : 3 === i2 ? "<math>" : "", c2 = v;
  for (let i3 = 0; i3 < s2; i3++) {
    const s3 = t2[i3];
    let a2, u2, d2 = -1, f2 = 0;
    for (; f2 < s3.length && (c2.lastIndex = f2, u2 = c2.exec(s3), null !== u2); ) f2 = c2.lastIndex, c2 === v ? "!--" === u2[1] ? c2 = _ : void 0 !== u2[1] ? c2 = m : void 0 !== u2[2] ? (y2.test(u2[2]) && (n3 = RegExp("</" + u2[2], "g")), c2 = p) : void 0 !== u2[3] && (c2 = p) : c2 === p ? ">" === u2[0] ? (c2 = n3 ?? v, d2 = -1) : void 0 === u2[1] ? d2 = -2 : (d2 = c2.lastIndex - u2[2].length, a2 = u2[1], c2 = void 0 === u2[3] ? p : '"' === u2[3] ? $ : g) : c2 === $ || c2 === g ? c2 = p : c2 === _ || c2 === m ? c2 = v : (c2 = p, n3 = void 0);
    const x2 = c2 === p && t2[i3 + 1].startsWith("/>") ? " " : "";
    l2 += c2 === v ? s3 + r$2 : d2 >= 0 ? (e2.push(a2), s3.slice(0, d2) + h + s3.slice(d2) + o$2 + x2) : s3 + o$2 + (-2 === d2 ? i3 : x2);
  }
  return [V(t2, l2 + (t2[s2] || "<?>") + (2 === i2 ? "</svg>" : 3 === i2 ? "</math>" : "")), e2];
};
class S {
  constructor({ strings: t2, _$litType$: i2 }, e2) {
    let r2;
    this.parts = [];
    let l2 = 0, a2 = 0;
    const u2 = t2.length - 1, d2 = this.parts, [f2, v2] = N(t2, i2);
    if (this.el = S.createElement(f2, e2), P.currentNode = this.el.content, 2 === i2 || 3 === i2) {
      const t3 = this.el.content.firstChild;
      t3.replaceWith(...t3.childNodes);
    }
    for (; null !== (r2 = P.nextNode()) && d2.length < u2; ) {
      if (1 === r2.nodeType) {
        if (r2.hasAttributes()) for (const t3 of r2.getAttributeNames()) if (t3.endsWith(h)) {
          const i3 = v2[a2++], s2 = r2.getAttribute(t3).split(o$2), e3 = /([.?@])?(.*)/.exec(i3);
          d2.push({ type: 1, index: l2, name: e3[2], strings: s2, ctor: "." === e3[1] ? I : "?" === e3[1] ? L : "@" === e3[1] ? z : H }), r2.removeAttribute(t3);
        } else t3.startsWith(o$2) && (d2.push({ type: 6, index: l2 }), r2.removeAttribute(t3));
        if (y2.test(r2.tagName)) {
          const t3 = r2.textContent.split(o$2), i3 = t3.length - 1;
          if (i3 > 0) {
            r2.textContent = s$1 ? s$1.emptyScript : "";
            for (let s2 = 0; s2 < i3; s2++) r2.append(t3[s2], c()), P.nextNode(), d2.push({ type: 2, index: ++l2 });
            r2.append(t3[i3], c());
          }
        }
      } else if (8 === r2.nodeType) if (r2.data === n$1) d2.push({ type: 2, index: l2 });
      else {
        let t3 = -1;
        for (; -1 !== (t3 = r2.data.indexOf(o$2, t3 + 1)); ) d2.push({ type: 7, index: l2 }), t3 += o$2.length - 1;
      }
      l2++;
    }
  }
  static createElement(t2, i2) {
    const s2 = l.createElement("template");
    return s2.innerHTML = t2, s2;
  }
}
function M(t2, i2, s2 = t2, e2) {
  var _a2, _b;
  if (i2 === E) return i2;
  let h2 = void 0 !== e2 ? (_a2 = s2._$Co) == null ? void 0 : _a2[e2] : s2._$Cl;
  const o2 = a(i2) ? void 0 : i2._$litDirective$;
  return (h2 == null ? void 0 : h2.constructor) !== o2 && ((_b = h2 == null ? void 0 : h2._$AO) == null ? void 0 : _b.call(h2, false), void 0 === o2 ? h2 = void 0 : (h2 = new o2(t2), h2._$AT(t2, s2, e2)), void 0 !== e2 ? (s2._$Co ?? (s2._$Co = []))[e2] = h2 : s2._$Cl = h2), void 0 !== h2 && (i2 = M(t2, h2._$AS(t2, i2.values), h2, e2)), i2;
}
class R {
  constructor(t2, i2) {
    this._$AV = [], this._$AN = void 0, this._$AD = t2, this._$AM = i2;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t2) {
    const { el: { content: i2 }, parts: s2 } = this._$AD, e2 = ((t2 == null ? void 0 : t2.creationScope) ?? l).importNode(i2, true);
    P.currentNode = e2;
    let h2 = P.nextNode(), o2 = 0, n3 = 0, r2 = s2[0];
    for (; void 0 !== r2; ) {
      if (o2 === r2.index) {
        let i3;
        2 === r2.type ? i3 = new k(h2, h2.nextSibling, this, t2) : 1 === r2.type ? i3 = new r2.ctor(h2, r2.name, r2.strings, this, t2) : 6 === r2.type && (i3 = new Z(h2, this, t2)), this._$AV.push(i3), r2 = s2[++n3];
      }
      o2 !== (r2 == null ? void 0 : r2.index) && (h2 = P.nextNode(), o2++);
    }
    return P.currentNode = l, e2;
  }
  p(t2) {
    let i2 = 0;
    for (const s2 of this._$AV) void 0 !== s2 && (void 0 !== s2.strings ? (s2._$AI(t2, s2, i2), i2 += s2.strings.length - 2) : s2._$AI(t2[i2])), i2++;
  }
}
class k {
  get _$AU() {
    var _a2;
    return ((_a2 = this._$AM) == null ? void 0 : _a2._$AU) ?? this._$Cv;
  }
  constructor(t2, i2, s2, e2) {
    this.type = 2, this._$AH = A, this._$AN = void 0, this._$AA = t2, this._$AB = i2, this._$AM = s2, this.options = e2, this._$Cv = (e2 == null ? void 0 : e2.isConnected) ?? true;
  }
  get parentNode() {
    let t2 = this._$AA.parentNode;
    const i2 = this._$AM;
    return void 0 !== i2 && 11 === (t2 == null ? void 0 : t2.nodeType) && (t2 = i2.parentNode), t2;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t2, i2 = this) {
    t2 = M(this, t2, i2), a(t2) ? t2 === A || null == t2 || "" === t2 ? (this._$AH !== A && this._$AR(), this._$AH = A) : t2 !== this._$AH && t2 !== E && this._(t2) : void 0 !== t2._$litType$ ? this.$(t2) : void 0 !== t2.nodeType ? this.T(t2) : d(t2) ? this.k(t2) : this._(t2);
  }
  O(t2) {
    return this._$AA.parentNode.insertBefore(t2, this._$AB);
  }
  T(t2) {
    this._$AH !== t2 && (this._$AR(), this._$AH = this.O(t2));
  }
  _(t2) {
    this._$AH !== A && a(this._$AH) ? this._$AA.nextSibling.data = t2 : this.T(l.createTextNode(t2)), this._$AH = t2;
  }
  $(t2) {
    var _a2;
    const { values: i2, _$litType$: s2 } = t2, e2 = "number" == typeof s2 ? this._$AC(t2) : (void 0 === s2.el && (s2.el = S.createElement(V(s2.h, s2.h[0]), this.options)), s2);
    if (((_a2 = this._$AH) == null ? void 0 : _a2._$AD) === e2) this._$AH.p(i2);
    else {
      const t3 = new R(e2, this), s3 = t3.u(this.options);
      t3.p(i2), this.T(s3), this._$AH = t3;
    }
  }
  _$AC(t2) {
    let i2 = C.get(t2.strings);
    return void 0 === i2 && C.set(t2.strings, i2 = new S(t2)), i2;
  }
  k(t2) {
    u(this._$AH) || (this._$AH = [], this._$AR());
    const i2 = this._$AH;
    let s2, e2 = 0;
    for (const h2 of t2) e2 === i2.length ? i2.push(s2 = new k(this.O(c()), this.O(c()), this, this.options)) : s2 = i2[e2], s2._$AI(h2), e2++;
    e2 < i2.length && (this._$AR(s2 && s2._$AB.nextSibling, e2), i2.length = e2);
  }
  _$AR(t2 = this._$AA.nextSibling, s2) {
    var _a2;
    for ((_a2 = this._$AP) == null ? void 0 : _a2.call(this, false, true, s2); t2 !== this._$AB; ) {
      const s3 = i$1(t2).nextSibling;
      i$1(t2).remove(), t2 = s3;
    }
  }
  setConnected(t2) {
    var _a2;
    void 0 === this._$AM && (this._$Cv = t2, (_a2 = this._$AP) == null ? void 0 : _a2.call(this, t2));
  }
}
class H {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t2, i2, s2, e2, h2) {
    this.type = 1, this._$AH = A, this._$AN = void 0, this.element = t2, this.name = i2, this._$AM = e2, this.options = h2, s2.length > 2 || "" !== s2[0] || "" !== s2[1] ? (this._$AH = Array(s2.length - 1).fill(new String()), this.strings = s2) : this._$AH = A;
  }
  _$AI(t2, i2 = this, s2, e2) {
    const h2 = this.strings;
    let o2 = false;
    if (void 0 === h2) t2 = M(this, t2, i2, 0), o2 = !a(t2) || t2 !== this._$AH && t2 !== E, o2 && (this._$AH = t2);
    else {
      const e3 = t2;
      let n3, r2;
      for (t2 = h2[0], n3 = 0; n3 < h2.length - 1; n3++) r2 = M(this, e3[s2 + n3], i2, n3), r2 === E && (r2 = this._$AH[n3]), o2 || (o2 = !a(r2) || r2 !== this._$AH[n3]), r2 === A ? t2 = A : t2 !== A && (t2 += (r2 ?? "") + h2[n3 + 1]), this._$AH[n3] = r2;
    }
    o2 && !e2 && this.j(t2);
  }
  j(t2) {
    t2 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t2 ?? "");
  }
}
class I extends H {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t2) {
    this.element[this.name] = t2 === A ? void 0 : t2;
  }
}
class L extends H {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t2) {
    this.element.toggleAttribute(this.name, !!t2 && t2 !== A);
  }
}
class z extends H {
  constructor(t2, i2, s2, e2, h2) {
    super(t2, i2, s2, e2, h2), this.type = 5;
  }
  _$AI(t2, i2 = this) {
    if ((t2 = M(this, t2, i2, 0) ?? A) === E) return;
    const s2 = this._$AH, e2 = t2 === A && s2 !== A || t2.capture !== s2.capture || t2.once !== s2.once || t2.passive !== s2.passive, h2 = t2 !== A && (s2 === A || e2);
    e2 && this.element.removeEventListener(this.name, this, s2), h2 && this.element.addEventListener(this.name, this, t2), this._$AH = t2;
  }
  handleEvent(t2) {
    var _a2;
    "function" == typeof this._$AH ? this._$AH.call(((_a2 = this.options) == null ? void 0 : _a2.host) ?? this.element, t2) : this._$AH.handleEvent(t2);
  }
}
class Z {
  constructor(t2, i2, s2) {
    this.element = t2, this.type = 6, this._$AN = void 0, this._$AM = i2, this.options = s2;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t2) {
    M(this, t2);
  }
}
const B = t$1.litHtmlPolyfillSupport;
B == null ? void 0 : B(S, k), (t$1.litHtmlVersions ?? (t$1.litHtmlVersions = [])).push("3.3.3");
const D = (t2, i2, s2) => {
  const e2 = (s2 == null ? void 0 : s2.renderBefore) ?? i2;
  let h2 = e2._$litPart$;
  if (void 0 === h2) {
    const t3 = (s2 == null ? void 0 : s2.renderBefore) ?? null;
    e2._$litPart$ = h2 = new k(i2.insertBefore(c(), t3), t3, void 0, s2 ?? {});
  }
  return h2._$AI(t2), h2;
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const s = globalThis;
class i extends y$1 {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    var _a2;
    const t2 = super.createRenderRoot();
    return (_a2 = this.renderOptions).renderBefore ?? (_a2.renderBefore = t2.firstChild), t2;
  }
  update(t2) {
    const r2 = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t2), this._$Do = D(r2, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    var _a2;
    super.connectedCallback(), (_a2 = this._$Do) == null ? void 0 : _a2.setConnected(true);
  }
  disconnectedCallback() {
    var _a2;
    super.disconnectedCallback(), (_a2 = this._$Do) == null ? void 0 : _a2.setConnected(false);
  }
  render() {
    return E;
  }
}
i._$litElement$ = true, i["finalized"] = true, (_a = s.litElementHydrateSupport) == null ? void 0 : _a.call(s, { LitElement: i });
const o$1 = s.litElementPolyfillSupport;
o$1 == null ? void 0 : o$1({ LitElement: i });
(s.litElementVersions ?? (s.litElementVersions = [])).push("4.2.2");
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const t = (t2) => (e2, o2) => {
  void 0 !== o2 ? o2.addInitializer(() => {
    customElements.define(t2, e2);
  }) : customElements.define(t2, e2);
};
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
const o = { attribute: true, type: String, converter: u$1, reflect: false, hasChanged: f$1 }, r$1 = (t2 = o, e2, r2) => {
  const { kind: n3, metadata: i2 } = r2;
  let s2 = globalThis.litPropertyMetadata.get(i2);
  if (void 0 === s2 && globalThis.litPropertyMetadata.set(i2, s2 = /* @__PURE__ */ new Map()), "setter" === n3 && ((t2 = Object.create(t2)).wrapped = true), s2.set(r2.name, t2), "accessor" === n3) {
    const { name: o2 } = r2;
    return { set(r3) {
      const n4 = e2.get.call(this);
      e2.set.call(this, r3), this.requestUpdate(o2, n4, t2, true, r3);
    }, init(e3) {
      return void 0 !== e3 && this.C(o2, void 0, t2, e3), e3;
    } };
  }
  if ("setter" === n3) {
    const { name: o2 } = r2;
    return function(r3) {
      const n4 = this[o2];
      e2.call(this, r3), this.requestUpdate(o2, n4, t2, true, r3);
    };
  }
  throw Error("Unsupported decorator location: " + n3);
};
function n2(t2) {
  return (e2, o2) => "object" == typeof o2 ? r$1(t2, e2, o2) : ((t3, e3, o3) => {
    const r2 = e3.hasOwnProperty(o3);
    return e3.constructor.createProperty(o3, t3), r2 ? Object.getOwnPropertyDescriptor(e3, o3) : void 0;
  })(t2, e2, o2);
}
/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
function r(r2) {
  return n2({ ...r2, state: true, attribute: false });
}
const ALL_SPACES_ID = "__all__";
function isCollapsibleUnchanged(entry, spaceId) {
  var _a2, _b;
  if (entry.kind === "plan") return false;
  if (entry.status === "error" || entry.status === "fallback" || entry.heuristic) {
    return false;
  }
  if (spaceId === ALL_SPACES_ID) {
    const records = Object.values(entry.spaces || {});
    if (records.length === 0) return true;
    return records.every(
      (rec2) => {
        var _a3;
        return !rec2.changed && !rec2.fallback && !rec2.locked && !((_a3 = rec2.comfort_boost) == null ? void 0 : _a3.applied);
      }
    );
  }
  const rec = (_a2 = entry.spaces) == null ? void 0 : _a2[spaceId];
  if (!rec) return false;
  if (rec.changed || rec.fallback || rec.locked) return false;
  if ((_b = rec.comfort_boost) == null ? void 0 : _b.applied) return false;
  return true;
}
function groupTimelineItems(entries, spaceId) {
  const items = [];
  let streak = [];
  const flushStreak = () => {
    if (streak.length === 0) return;
    if (streak.length === 1) {
      items.push({ type: "entry", entry: streak[0] });
    } else {
      items.push({
        type: "collapsed",
        id: `streak_${streak[0].id}_${streak[streak.length - 1].id}`,
        entries: [...streak]
      });
    }
    streak = [];
  };
  for (const entry of entries) {
    if (isCollapsibleUnchanged(entry, spaceId)) {
      streak.push(entry);
    } else {
      flushStreak();
      items.push({ type: "entry", entry });
    }
  }
  flushStreak();
  return items;
}
function formatShortTimestamp(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const now = /* @__PURE__ */ new Date();
  const sameDay = date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
  const timeStr = date.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit"
  });
  if (sameDay) {
    return `Today ${timeStr}`;
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday = date.getFullYear() === yesterday.getFullYear() && date.getMonth() === yesterday.getMonth() && date.getDate() === yesterday.getDate();
  if (isYesterday) {
    return `Yesterday ${timeStr}`;
  }
  const dayStr = date.toLocaleDateString([], { weekday: "short" });
  return `${dayStr} ${timeStr}`;
}
function formatFullTimestamp(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}
function formatStreakRange(entries) {
  if (entries.length === 0) return "";
  const newest = entries[0].timestamp;
  const oldest = entries[entries.length - 1].timestamp;
  return `${formatShortTimestamp(oldest)} – ${formatShortTimestamp(newest)}`;
}
function formatTriggerLabel(trigger) {
  if (!trigger) return "Event";
  if (trigger.label) return trigger.label;
  switch (trigger.type) {
    case "scheduled_plan":
    case "manual_plan":
      return "Plan";
    case "presence_change":
      return "Presence";
    case "alarm_change":
      return "Arm/Disarm";
    case "manual_intraday":
      return "Manual Check";
    default:
      return trigger.type.replace(/_/g, " ");
  }
}
function formatTriggerDetail(trigger) {
  if (!trigger) return "";
  if (trigger.type === "manual_plan") {
    return "Triggered manually (Run Plan)";
  }
  if (trigger.type === "manual_intraday") {
    return "Triggered manually (Check Now)";
  }
  if (trigger.type === "scheduled_plan") {
    return "Scheduled nightly macro-plan";
  }
  if (trigger.type === "presence_change") {
    const sensor = trigger.sensor || "presence sensor";
    const to = trigger.to || trigger.state || "?";
    const transition = trigger.from ? `${trigger.from} → ${to}` : `→ ${to}`;
    const dur = trigger.for_minutes ? ` (${trigger.for_minutes}m)` : "";
    return `Triggered by ${sensor} ${transition}${dur}`;
  }
  if (trigger.type === "alarm_change") {
    const from = trigger.from || "?";
    const to = trigger.to || "?";
    return `Triggered by alarm ${from} → ${to}`;
  }
  return `Triggered by ${trigger.type}`;
}
function formatWeatherSummary(weather) {
  if (!weather) return "";
  const parts = [];
  const cur = weather.current;
  if (cur && cur.temperature != null) {
    const cond = cur.condition ? ` ${cur.condition}` : "";
    const wind = cur.wind_speed != null ? `, ${Math.round(cur.wind_speed)} mph wind` : "";
    parts.push(`Now ${Math.round(cur.temperature)}°F${cond}${wind}`);
  }
  const tom = weather.tomorrow_daily;
  if (tom && (tom.temp_low != null || tom.temp_high != null)) {
    const low = tom.temp_low != null ? `${Math.round(tom.temp_low)}°` : "?";
    const high = tom.temp_high != null ? `${Math.round(tom.temp_high)}°F` : "?";
    const cond = tom.condition ? ` ${tom.condition}` : "";
    parts.push(`Tomorrow ${low}–${high}${cond}`);
  }
  return parts.join(" · ");
}
function trimSeconds(timeStr) {
  if (!timeStr) return "";
  if (timeStr.startsWith("23:59:59")) return "24:00";
  const parts = timeStr.split(":");
  if (parts.length >= 2) {
    return `${parts[0]}:${parts[1]}`;
  }
  return timeStr;
}
function formatBlockLine(block) {
  const from = trimSeconds(block.from);
  const to = trimSeconds(block.to);
  const d2 = block.data || {};
  const mode = String(d2.hvac_mode || "heat_cool").toLowerCase();
  if (mode === "off") {
    return `${from}–${to}  Off`;
  }
  if (mode === "heat" && d2.heat_to != null) {
    return `${from}–${to}  Heat ${d2.heat_to}°F`;
  }
  if (mode === "cool" && d2.cool_to != null) {
    return `${from}–${to}  Cool ${d2.cool_to}°F`;
  }
  if (d2.heat_to != null && d2.cool_to != null) {
    return `${from}–${to}  ${d2.heat_to}°–${d2.cool_to}°F`;
  }
  return `${from}–${to}  ${mode}`;
}
function computeChangedDays(rec) {
  const beforeMap = rec.before_blocks || {};
  const afterMap = rec.after_blocks || {};
  const days = Array.from(/* @__PURE__ */ new Set([...Object.keys(beforeMap), ...Object.keys(afterMap)]));
  const diffs = [];
  for (const day of days) {
    const b2 = beforeMap[day] || [];
    const a2 = afterMap[day] || [];
    if (JSON.stringify(b2) !== JSON.stringify(a2)) {
      diffs.push({ day, before: b2, after: a2 });
    }
  }
  return diffs;
}
function capitalize(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : "";
}
var __defProp$3 = Object.defineProperty;
var __getOwnPropDesc$3 = Object.getOwnPropertyDescriptor;
var __decorateClass$3 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$3(target, key) : target;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$3(target, key, result);
  return result;
};
let ButlerTimelineView = class extends i {
  constructor() {
    super(...arguments);
    this.entries = [];
    this.latestPlan = null;
    this.selectedSpaceId = "";
    this._expandedStreaks = /* @__PURE__ */ new Set();
  }
  _toggleStreak(id) {
    const next = new Set(this._expandedStreaks);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    this._expandedStreaks = next;
  }
  _selectEntry(entry) {
    this.dispatchEvent(
      new CustomEvent("select-entry", {
        detail: { entry },
        bubbles: true,
        composed: true
      })
    );
  }
  _triggerBadgeClass(entry) {
    var _a2;
    const t2 = (_a2 = entry.trigger) == null ? void 0 : _a2.type;
    if (t2 === "presence_change") return "badge-trigger-presence";
    if (t2 === "alarm_change") return "badge-trigger-alarm";
    if (t2 === "calendar_event") return "badge-trigger-calendar";
    return "badge-trigger-plan";
  }
  _renderEntryRow(entry) {
    var _a2, _b;
    const isAll = this.selectedSpaceId === ALL_SPACES_ID;
    const isPlan = entry.kind === "plan";
    const allRecs = Object.values(entry.spaces || {});
    const rec = isAll ? void 0 : (_a2 = entry.spaces) == null ? void 0 : _a2[this.selectedSpaceId];
    const isHeuristic = Boolean(entry.heuristic);
    const anyFallback = isAll ? allRecs.some((r2) => r2.fallback) : Boolean(rec == null ? void 0 : rec.fallback);
    const changedRecs = allRecs.filter((r2) => r2.changed);
    const anyChanged = isAll ? changedRecs.length > 0 : Boolean(rec == null ? void 0 : rec.changed);
    const anyBoost = isAll ? allRecs.some((r2) => {
      var _a3;
      return (_a3 = r2.comfort_boost) == null ? void 0 : _a3.applied;
    }) : Boolean((_b = rec == null ? void 0 : rec.comfort_boost) == null ? void 0 : _b.applied);
    const isUnchangedIntraday = !isPlan && !anyChanged && !anyFallback && !isHeuristic && !anyBoost;
    let summaryText;
    if (!isAll) {
      summaryText = (rec == null ? void 0 : rec.summary) || entry.headline || "No details recorded.";
    } else if (allRecs.length === 1) {
      summaryText = `${allRecs[0].name}: ${allRecs[0].summary}`;
    } else if (changedRecs.length === 1) {
      summaryText = `${changedRecs[0].name}: ${changedRecs[0].summary}`;
    } else {
      summaryText = entry.headline || "No details recorded.";
    }
    return b`
      <div
        class="row ${isPlan ? "plan-anchor" : ""} ${isUnchangedIntraday ? "unchanged-intraday" : ""}"
        role="button"
        tabindex="0"
        @click=${() => this._selectEntry(entry)}
        @keydown=${(e2) => {
      if (e2.key === "Enter" || e2.key === " ") {
        e2.preventDefault();
        this._selectEntry(entry);
      }
    }}
      >
        <div class="row-top">
          <div class="badges">
            <span
              class="badge ${this._triggerBadgeClass(entry)}"
              title="Deterministic trigger that started this evaluation"
            >
              ${formatTriggerLabel(entry.trigger)}
            </span>
            ${entry.status === "error" ? b`<span class="badge badge-error">Error</span>` : A}
            ${isHeuristic ? b`<span
                  class="badge badge-fallback"
                  title="AI unavailable — ran in basic non-AI mode"
                >
                  Basic
                </span>` : A}
            ${anyFallback ? b`<span class="badge badge-fallback">Fallback</span>` : anyChanged ? b`<span class="badge badge-adjusted">
                    ${isAll && changedRecs.length > 1 ? `${changedRecs.length} Adjusted` : "Adjusted"}
                  </span>` : A}
            ${anyBoost ? b`<span class="badge badge-boost">Comfort Boost</span>` : A}
          </div>
          <span class="time">${formatShortTimestamp(entry.timestamp)}</span>
        </div>
        <div class="summary">${summaryText}</div>
      </div>
    `;
  }
  render() {
    var _a2, _b;
    if (!this.selectedSpaceId) {
      return b`<div class="empty-state">No spaces configured in HVAC Butler.</div>`;
    }
    const isAll = this.selectedSpaceId === ALL_SPACES_ID;
    const spaceEntries = isAll ? this.entries : this.entries.filter(
      (e2) => e2.spaces && this.selectedSpaceId in e2.spaces
    );
    if (spaceEntries.length === 0) {
      return b`
        <div class="empty-state">
          No activity recorded yet${isAll ? "" : " for this space"}. Use
          <strong>Run Plan</strong> to generate a plan now.
        </div>
      `;
    }
    const items = groupTimelineItems(spaceEntries, this.selectedSpaceId);
    const fallbackPlan = this.latestPlan && (isAll || this.latestPlan.spaces && this.selectedSpaceId in this.latestPlan.spaces) ? this.latestPlan : null;
    const latestPlan = spaceEntries.find((e2) => e2.kind === "plan") ?? fallbackPlan;
    const isPlanAlreadyTop = Boolean(latestPlan) && ((_a2 = items[0]) == null ? void 0 : _a2.type) === "entry" && items[0].entry.id === (latestPlan == null ? void 0 : latestPlan.id);
    const showPinnedPlan = Boolean(latestPlan) && !isPlanAlreadyTop;
    let pinnedPlanText = "";
    if (showPinnedPlan && latestPlan) {
      const rec = isAll ? void 0 : (_b = latestPlan.spaces) == null ? void 0 : _b[this.selectedSpaceId];
      pinnedPlanText = !isAll ? (rec == null ? void 0 : rec.summary) || latestPlan.headline || "Plan updated." : latestPlan.headline || "Plan updated.";
    }
    return b`
      ${showPinnedPlan && latestPlan ? b`
            <div
              class="pinned-plan ${latestPlan.heuristic ? "heuristic" : ""}"
              role="button"
              tabindex="0"
              title="Latest daily plan — click for full schedule details"
              @click=${() => this._selectEntry(latestPlan)}
              @keydown=${(e2) => {
      if (e2.key === "Enter" || e2.key === " ") {
        e2.preventDefault();
        this._selectEntry(latestPlan);
      }
    }}
            >
              <div class="pinned-plan-left">
                <span class="badge badge-trigger-plan">Plan</span>
                ${latestPlan.heuristic ? b`<span
                      class="badge badge-fallback"
                      title="AI unavailable — plan generated in basic non-AI mode"
                    >
                      Basic
                    </span>` : A}
                <span class="pinned-plan-text">${pinnedPlanText}</span>
              </div>
              <span class="time">${formatShortTimestamp(latestPlan.timestamp)}</span>
            </div>
          ` : A}
      <div class="timeline-scroll">
        <div class="timeline">
          ${items.map((item) => {
      if (item.type === "entry") {
        return this._renderEntryRow(item.entry);
      }
      const expanded = this._expandedStreaks.has(item.id);
      return b`
              <div
                class="collapsed-row"
                role="button"
                tabindex="0"
                @click=${() => this._toggleStreak(item.id)}
                @keydown=${(e2) => {
        if (e2.key === "Enter" || e2.key === " ") {
          e2.preventDefault();
          this._toggleStreak(item.id);
        }
      }}
              >
                <span class="collapsed-left">
                  <span>${expanded ? "▾" : "▸"}</span>
                  <span>${item.entries.length} unchanged checks</span>
                </span>
                <span class="time">${formatStreakRange(item.entries)}</span>
              </div>
              ${expanded ? b`
                    <div class="streak-children">
                      ${item.entries.map((e2) => this._renderEntryRow(e2))}
                    </div>
                  ` : A}
            `;
    })}
        </div>
      </div>
    `;
  }
};
ButlerTimelineView.styles = i$3`
    :host {
      display: block;
    }

    .empty-state {
      padding: 24px 12px;
      text-align: center;
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 0.9rem;
    }

    .pinned-plan {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 6px 10px;
      margin-bottom: 8px;
      border-radius: 8px;
      border: 1px solid rgba(3, 169, 244, 0.28);
      border-left: 3px solid var(--primary-color, #03a9f4);
      background: rgba(3, 169, 244, 0.07);
      cursor: pointer;
      transition: background 0.15s ease, border-color 0.15s ease;
      min-width: 0;
    }

    .pinned-plan:hover {
      background: rgba(3, 169, 244, 0.14);
      border-color: var(--primary-color, #03a9f4);
    }

    .pinned-plan.heuristic {
      border-color: rgba(255, 152, 0, 0.35);
      border-left-color: #ffb74d;
      background: rgba(255, 152, 0, 0.08);
    }

    .pinned-plan.heuristic:hover {
      background: rgba(255, 152, 0, 0.15);
      border-color: #ffb74d;
    }

    .pinned-plan-left {
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
      flex: 1 1 auto;
    }

    .pinned-plan-text {
      font-size: 0.8rem;
      color: var(--primary-text-color, #e1e1e1);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
    }

    .timeline-scroll {
      max-height: 360px;
      overflow-y: auto;
      overscroll-behavior-y: auto;
      -webkit-overflow-scrolling: touch;
      padding-right: 2px;
      scrollbar-width: thin;
      scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
    }

    .timeline-scroll::-webkit-scrollbar {
      width: 5px;
    }

    .timeline-scroll::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.2);
      border-radius: 999px;
    }

    .timeline-scroll::-webkit-scrollbar-track {
      background: transparent;
    }

    .timeline {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .row {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px 10px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      background: var(--secondary-background-color, rgba(127, 127, 127, 0.06));
      cursor: pointer;
      transition: background 0.15s ease, border-color 0.15s ease;
      text-align: left;
    }

    .row:hover {
      background: rgba(127, 127, 127, 0.14);
      border-color: var(--primary-color, #03a9f4);
    }

    .row.plan-anchor {
      border-left: 3px solid var(--primary-color, #03a9f4);
      background: rgba(3, 169, 244, 0.05);
    }

    .row.plan-anchor:hover {
      background: rgba(3, 169, 244, 0.11);
    }

    .row.unchanged-intraday {
      opacity: 0.8;
    }

    .row-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }

    .badges {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .badge {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      white-space: nowrap;
    }

    .badge-trigger-plan {
      background: rgba(3, 169, 244, 0.18);
      color: var(--primary-color, #29b6f6);
    }

    .badge-trigger-presence {
      background: rgba(156, 39, 176, 0.18);
      color: #ce93d8;
    }

    .badge-trigger-alarm {
      background: rgba(255, 152, 0, 0.18);
      color: #ffb74d;
    }

    .badge-trigger-calendar {
      background: rgba(0, 188, 212, 0.18);
      color: #4dd0e1;
    }

    .badge-adjusted {
      background: rgba(76, 175, 80, 0.18);
      color: #81c784;
    }

    .badge-boost {
      background: rgba(255, 112, 67, 0.2);
      color: #ff8a65;
    }

    .badge-fallback {
      background: rgba(255, 152, 0, 0.22);
      color: #ffb74d;
    }

    .badge-error {
      background: rgba(244, 67, 54, 0.2);
      color: #ef5350;
    }

    .time {
      font-size: 0.76rem;
      color: var(--secondary-text-color, #9e9e9e);
      white-space: nowrap;
    }

    .summary {
      font-size: 0.86rem;
      line-height: 1.4;
      color: var(--primary-text-color, #e1e1e1);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .collapsed-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 7px 12px;
      border-radius: 8px;
      border: 1px dashed var(--divider-color, rgba(255, 255, 255, 0.16));
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 0.8rem;
      cursor: pointer;
      user-select: none;
    }

    .collapsed-row:hover {
      background: rgba(127, 127, 127, 0.1);
      color: var(--primary-text-color, #e1e1e1);
    }

    .collapsed-left {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
    }

    .streak-children {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding-left: 12px;
      border-left: 2px solid var(--divider-color, rgba(255, 255, 255, 0.12));
    }
  `;
__decorateClass$3([
  n2({ attribute: false })
], ButlerTimelineView.prototype, "entries", 2);
__decorateClass$3([
  n2({ attribute: false })
], ButlerTimelineView.prototype, "latestPlan", 2);
__decorateClass$3([
  n2({ type: String })
], ButlerTimelineView.prototype, "selectedSpaceId", 2);
__decorateClass$3([
  r()
], ButlerTimelineView.prototype, "_expandedStreaks", 2);
ButlerTimelineView = __decorateClass$3([
  t("butler-timeline-view")
], ButlerTimelineView);
var __defProp$2 = Object.defineProperty;
var __getOwnPropDesc$2 = Object.getOwnPropertyDescriptor;
var __decorateClass$2 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$2(target, key) : target;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$2(target, key, result);
  return result;
};
let ButlerDetailModal = class extends i {
  constructor() {
    super(...arguments);
    this.entry = null;
    this.selectedSpaceId = "";
    this._handleKeyDown = (ev) => {
      if (ev.key === "Escape") {
        this._close();
      }
    };
  }
  connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", this._handleKeyDown);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this._handleKeyDown);
  }
  _handleBackdropClick(ev) {
    if (ev.target === ev.currentTarget) {
      this._close();
    }
  }
  _close() {
    this.dispatchEvent(new CustomEvent("close-modal", { bubbles: true, composed: true }));
  }
  _triggerBadgeClass(entry) {
    var _a2;
    const t2 = (_a2 = entry.trigger) == null ? void 0 : _a2.type;
    if (t2 === "presence_change") return "badge-trigger-presence";
    if (t2 === "alarm_change") return "badge-trigger-alarm";
    return "badge-trigger-plan";
  }
  _renderSpaceBadges(rec) {
    return b`
      <div class="badges">
        ${rec.locked ? b`<span class="badge badge-fallback">Edit Locked</span>` : A}
        ${rec.fallback ? b`<span class="badge badge-fallback">Fallback</span>` : rec.changed ? b`<span class="badge badge-adjusted">Adjusted</span>` : b`<span class="badge badge-unchanged">Unchanged</span>`}
        ${rec.comfort_boost ? b`<span class="badge badge-boost">Comfort Boost</span>` : A}
      </div>
    `;
  }
  _renderSpaceDiff(rec) {
    const diffs = computeChangedDays(rec);
    if (diffs.length === 0) return A;
    return b`
      <div class="diff-box">
        ${diffs.map(
      (d2) => b`
            <div class="diff-day">
              <div class="diff-day-title">${capitalize(d2.day)} schedule</div>
              <div class="diff-columns">
                <div>
                  <div class="diff-col-label">Before</div>
                  ${d2.before.length ? d2.before.map(
        (b$12) => b`<div class="diff-line">${formatBlockLine(b$12)}</div>`
      ) : b`<div class="diff-line">(none)</div>`}
                </div>
                <div>
                  <div class="diff-col-label">After</div>
                  ${d2.after.length ? d2.after.map(
        (b$12) => b`<div class="diff-line">${formatBlockLine(b$12)}</div>`
      ) : b`<div class="diff-line">(none)</div>`}
                </div>
              </div>
            </div>
          `
    )}
      </div>
    `;
  }
  _renderOtherSpaceItem(rec) {
    return b`
      <div class="other-space-item ${rec.changed ? "" : "unchanged"}">
        <div class="space-header">
          <span class="space-name">${rec.name}</span>
          ${this._renderSpaceBadges(rec)}
        </div>
        <p class="summary-text">${rec.summary}</p>
        ${rec.changed ? this._renderSpaceDiff(rec) : A}
      </div>
    `;
  }
  render() {
    const entry = this.entry;
    if (!entry) return A;
    const spacesMap = entry.spaces || {};
    const isAll = this.selectedSpaceId === ALL_SPACES_ID;
    const selectedRec = !isAll && this.selectedSpaceId ? spacesMap[this.selectedSpaceId] : void 0;
    const otherEntries = Object.entries(spacesMap).filter(
      ([sid]) => isAll || sid !== this.selectedSpaceId
    );
    const otherChanged = otherEntries.filter(([, r2]) => r2.changed || r2.fallback);
    const otherUnchanged = otherEntries.filter(([, r2]) => !r2.changed && !r2.fallback);
    const weatherLine = formatWeatherSummary(entry.weather_snapshot);
    const triggerDetail = formatTriggerDetail(entry.trigger);
    const allGuardrailNotes = [];
    for (const [, rec] of Object.entries(spacesMap)) {
      for (const note of rec.guardrail_notes || []) {
        allGuardrailNotes.push(`${rec.name}: ${note}`);
      }
    }
    return b`
      <div class="dialog" @click=${(e2) => e2.stopPropagation()}>
        <div class="modal-header">
          <div class="header-left">
            <span class="badge ${this._triggerBadgeClass(entry)}">
              ${formatTriggerLabel(entry.trigger)}
            </span>
            ${entry.status === "error" ? b`<span class="badge badge-error">Error</span>` : A}
            ${entry.heuristic ? b`<span
                  class="badge badge-fallback"
                  title="AI unavailable — ran in basic non-AI mode"
                >
                  Basic
                </span>` : A}
            <span class="timestamp">${formatFullTimestamp(entry.timestamp)}</span>
          </div>
          <button
            class="close-btn"
            @click=${this._close}
            aria-label="Close details"
            title="Close"
          >
            ×
          </button>
        </div>

        <div class="modal-body">
          <div class="context-strip">
            <div>${triggerDetail}</div>
            ${weatherLine ? b`<div>${weatherLine}</div>` : A}
          </div>

          ${entry.heuristic ? b`<div class="heuristic-banner">
                AI unavailable — ran in basic mode${entry.error ? `: ${entry.error}` : "."}
              </div>` : entry.error ? b`<div class="error-banner">${entry.error}</div>` : A}

          ${selectedRec ? b`
                <div>
                  <div class="section-label">Selected Space</div>
                  <div class="featured-space">
                    <div class="space-header">
                      <span class="space-name">${selectedRec.name}</span>
                      ${this._renderSpaceBadges(selectedRec)}
                    </div>
                    <p class="summary-text">${selectedRec.summary}</p>
                    ${selectedRec.comfort_boost ? b`
                          <div class="boost-detail">
                            Comfort Boost:
                            ${selectedRec.comfort_boost.feeling === "too_cold" ? "+" : "-"}
                            ${selectedRec.comfort_boost.delta_f}°F
                            (${selectedRec.comfort_boost.duration_minutes}m)
                            ${selectedRec.comfort_boost.applied ? "— applied" : "— not applied (space not on Butler preset)"}
                          </div>
                        ` : A}
                    ${this._renderSpaceDiff(selectedRec)}
                  </div>
                </div>
              ` : A}

          ${otherEntries.length > 0 ? b`
                <div>
                  <div class="section-label">
                    ${selectedRec ? "Other Spaces in This Evaluation" : "Spaces"}
                  </div>
                  <div class="other-spaces-list">
                    ${otherChanged.map(([, rec]) => this._renderOtherSpaceItem(rec))}
                    ${otherUnchanged.length > (selectedRec ? 3 : 4) ? b`
                          <details class="accordion">
                            <summary>
                              ${selectedRec ? "Other unchanged spaces" : "Unchanged spaces"}
                              (${otherUnchanged.length})
                            </summary>
                            <div class="other-spaces-list">
                              ${otherUnchanged.map(
      ([, rec]) => this._renderOtherSpaceItem(rec)
    )}
                            </div>
                          </details>
                        ` : otherUnchanged.map(
      ([, rec]) => this._renderOtherSpaceItem(rec)
    )}
                  </div>
                </div>
              ` : A}

          <details class="accordion">
            <summary>Technical details</summary>
            ${allGuardrailNotes.length > 0 ? b`
                  <div class="section-label">Guardrail Notes</div>
                  <ul class="guardrail-list">
                    ${allGuardrailNotes.map((n3) => b`<li>${n3}</li>`)}
                  </ul>
                ` : A}
            <div class="section-label">
              Record v${entry.schema_version ?? 1} · Raw AI Output
            </div>
            <pre class="raw-json">${JSON.stringify(entry.raw_response ?? null, null, 2)}</pre>
          </details>
        </div>
      </div>
    `;
  }
  firstUpdated() {
    this.addEventListener("click", (ev) => this._handleBackdropClick(ev));
  }
};
ButlerDetailModal.styles = i$3`
    :host {
      position: fixed;
      inset: 0;
      z-index: 999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      background: rgba(0, 0, 0, 0.55);
      backdrop-filter: blur(2px);
      box-sizing: border-box;
    }

    .dialog {
      background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
      border-radius: 14px;
      width: 100%;
      max-width: 600px;
      max-height: 82vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
      overflow: hidden;
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      min-width: 0;
    }

    .timestamp {
      font-size: 0.92rem;
      font-weight: 600;
    }

    .close-btn {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 1.4rem;
      line-height: 1;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
    }

    .close-btn:hover {
      background: rgba(127, 127, 127, 0.18);
      color: var(--primary-text-color, #fff);
    }

    .modal-body {
      padding: 16px 18px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .context-strip {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-size: 0.82rem;
      color: var(--secondary-text-color, #9e9e9e);
      background: rgba(127, 127, 127, 0.08);
      padding: 8px 12px;
      border-radius: 8px;
    }

    .error-banner {
      background: rgba(244, 67, 54, 0.14);
      border: 1px solid rgba(244, 67, 54, 0.35);
      color: var(--error-color, #ef5350);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
    }

    .heuristic-banner {
      background: rgba(255, 152, 0, 0.14);
      border: 1px solid rgba(255, 152, 0, 0.35);
      color: #ffb74d;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
    }

    .section-label {
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--secondary-text-color, #9e9e9e);
      margin-bottom: 6px;
    }

    .featured-space {
      border: 1px solid var(--primary-color, #03a9f4);
      background: rgba(3, 169, 244, 0.06);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .space-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }

    .space-name {
      font-weight: 600;
      font-size: 0.96rem;
    }

    .badges {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .badge {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      white-space: nowrap;
    }

    .badge-trigger-plan {
      background: rgba(3, 169, 244, 0.18);
      color: var(--primary-color, #29b6f6);
    }

    .badge-trigger-presence {
      background: rgba(156, 39, 176, 0.18);
      color: #ce93d8;
    }

    .badge-trigger-alarm {
      background: rgba(255, 152, 0, 0.18);
      color: #ffb74d;
    }

    .badge-adjusted {
      background: rgba(76, 175, 80, 0.18);
      color: #81c784;
    }

    .badge-unchanged {
      background: rgba(127, 127, 127, 0.16);
      color: var(--secondary-text-color, #9e9e9e);
    }

    .badge-boost {
      background: rgba(255, 112, 67, 0.2);
      color: #ff8a65;
    }

    .badge-fallback {
      background: rgba(255, 152, 0, 0.22);
      color: #ffb74d;
    }

    .badge-error {
      background: rgba(244, 67, 54, 0.2);
      color: #ef5350;
    }

    .summary-text {
      font-size: 0.9rem;
      line-height: 1.48;
      margin: 0;
    }

    .boost-detail {
      font-size: 0.82rem;
      color: #ff8a65;
      background: rgba(255, 112, 67, 0.1);
      padding: 6px 10px;
      border-radius: 6px;
    }

    .diff-box {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 2px;
    }

    .diff-day {
      background: rgba(127, 127, 127, 0.08);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 0.8rem;
    }

    .diff-day-title {
      font-weight: 600;
      margin-bottom: 6px;
      color: var(--primary-text-color, #e1e1e1);
    }

    .diff-columns {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    @media (max-width: 500px) {
      .diff-columns {
        grid-template-columns: 1fr;
      }
    }

    .diff-col-label {
      font-size: 0.72rem;
      color: var(--secondary-text-color, #9e9e9e);
      margin-bottom: 3px;
    }

    .diff-line {
      font-family: var(--code-font-family, monospace);
      font-size: 0.76rem;
      line-height: 1.4;
    }

    .other-spaces-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .other-space-item {
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      border-radius: 8px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .other-space-item.unchanged {
      opacity: 0.88;
    }

    details.accordion {
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.84rem;
    }

    details.accordion summary {
      cursor: pointer;
      color: var(--secondary-text-color, #9e9e9e);
      font-weight: 500;
      user-select: none;
    }

    details.accordion[open] summary {
      margin-bottom: 8px;
    }

    .guardrail-list {
      margin: 0 0 8px 0;
      padding-left: 18px;
      font-size: 0.8rem;
      color: #ffb74d;
    }

    pre.raw-json {
      margin: 0;
      padding: 10px;
      border-radius: 6px;
      background: rgba(0, 0, 0, 0.25);
      font-size: 0.74rem;
      overflow-x: auto;
      max-height: 220px;
      white-space: pre-wrap;
      word-break: break-word;
    }
  `;
__decorateClass$2([
  n2({ attribute: false })
], ButlerDetailModal.prototype, "entry", 2);
__decorateClass$2([
  n2({ type: String })
], ButlerDetailModal.prototype, "selectedSpaceId", 2);
ButlerDetailModal = __decorateClass$2([
  t("butler-detail-modal")
], ButlerDetailModal);
const BUTLER_HEAD_DATA_URI = "data:image/png;base64,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";
var __defProp$1 = Object.defineProperty;
var __getOwnPropDesc$1 = Object.getOwnPropertyDescriptor;
var __decorateClass$1 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$1(target, key) : target;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$1(target, key, result);
  return result;
};
function greetingForHour(hour) {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
let ButlerBriefModal = class extends i {
  constructor() {
    super(...arguments);
    this._messages = [];
    this._pendingActions = [];
    this._draft = "";
    this._sending = false;
    this._committing = false;
    this._error = null;
    this._handleKeydown = (e2) => {
      if (e2.key === "Escape" && !this._committing) {
        this._cancel();
      }
    };
  }
  connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", this._handleKeydown);
    if (this._messages.length === 0) {
      const greeting = greetingForHour((/* @__PURE__ */ new Date()).getHours());
      this._messages = [
        {
          role: "assistant",
          content: `${greeting}! Tell me about any upcoming guests, events, travel, or schedule changes—I'll ask any quick HVAC questions and note them on my calendar.`
        }
      ];
    }
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this._handleKeydown);
  }
  _cancel() {
    this.dispatchEvent(
      new CustomEvent("close-brief", { bubbles: true, composed: true })
    );
  }
  _scrollToBottom() {
    void this.updateComplete.then(() => {
      const el = this.renderRoot.querySelector(".messages");
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    });
  }
  async _send() {
    const text = this._draft.trim();
    if (!text || !this.hass || this._sending || this._committing) return;
    const nextMessages = [
      ...this._messages,
      { role: "user", content: text }
    ];
    this._messages = nextMessages;
    this._draft = "";
    this._error = null;
    this._sending = true;
    this._scrollToBottom();
    try {
      const resp = await this.hass.callWS({
        type: "hvac_butler/brief",
        messages: nextMessages
      });
      this._messages = [
        ...nextMessages,
        { role: "assistant", content: resp.reply || "Noted." }
      ];
      if (Array.isArray(resp.calendar_actions) && resp.calendar_actions.length > 0) {
        this._pendingActions = resp.calendar_actions;
      }
      this._scrollToBottom();
    } catch (err) {
      this._error = err instanceof Error ? err.message : (err == null ? void 0 : err.message) || "Failed to reach HVAC Butler.";
    } finally {
      this._sending = false;
    }
  }
  async _done() {
    if (this._committing || this._sending) return;
    const pendingText = this._draft.trim();
    const finalMessages = pendingText ? [...this._messages, { role: "user", content: pendingText }] : [...this._messages];
    const hasUserMessage = finalMessages.some((m2) => m2.role === "user");
    if (!hasUserMessage || !this.hass) {
      this._cancel();
      return;
    }
    const actionsToSend = pendingText ? [] : this._pendingActions;
    this._messages = finalMessages;
    this._draft = "";
    this._error = null;
    this._committing = true;
    try {
      const resp = await this.hass.callWS({
        type: "hvac_butler/brief_commit",
        messages: finalMessages,
        calendar_actions: actionsToSend
      });
      this.dispatchEvent(
        new CustomEvent("brief-committed", {
          detail: resp,
          bubbles: true,
          composed: true
        })
      );
      this._cancel();
    } catch (err) {
      this._error = err instanceof Error ? err.message : (err == null ? void 0 : err.message) || "Failed to save calendar notes.";
      this._committing = false;
    }
  }
  render() {
    const busy = this._sending || this._committing;
    return b`
      <div
        class="dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Call Butler"
        @click=${(e2) => e2.stopPropagation()}
      >
        <div class="header">
          <div class="header-left">
            <img class="header-avatar" src=${BUTLER_HEAD_DATA_URI} alt="" />
            <div class="header-titles">
              <span class="header-title">Call Butler</span>
              <span class="header-sub">
                Discuss upcoming events for Butler's calendar
              </span>
            </div>
          </div>
          <button
            class="close-btn"
            aria-label="Close"
            ?disabled=${this._committing}
            @click=${this._cancel}
          >
            &times;
          </button>
        </div>

        <div class="messages">
          ${this._messages.map(
      (m2) => b`
              <div class="msg-row ${m2.role}">
                ${m2.role === "assistant" ? b`<img class="msg-avatar" src=${BUTLER_HEAD_DATA_URI} alt="" />` : A}
                <div class="bubble">${m2.content}</div>
              </div>
            `
    )}
          ${this._sending ? b`
                <div class="msg-row assistant">
                  <img class="msg-avatar" src=${BUTLER_HEAD_DATA_URI} alt="" />
                  <div class="bubble typing">Thinking…</div>
                </div>
              ` : A}
        </div>

        ${this._error ? b`<div class="error-banner">${this._error}</div>` : A}

        <div class="composer">
          <textarea
            rows="2"
            placeholder="Tell the butler about upcoming events that affect the home's climate controls."
            .value=${this._draft}
            ?disabled=${busy}
            @input=${(e2) => {
      this._draft = e2.target.value;
    }}
            @keydown=${(e2) => {
      if (e2.key === "Enter" && !e2.shiftKey) {
        e2.preventDefault();
        void this._send();
      }
    }}
          ></textarea>
          <button
            class="send-btn"
            ?disabled=${busy || !this._draft.trim()}
            @click=${() => void this._send()}
          >
            Send
          </button>
        </div>

        <div class="footer">
          <button
            class="cancel-btn"
            ?disabled=${this._committing}
            @click=${this._cancel}
          >
            Cancel
          </button>
          <button
            class="done-btn"
            ?disabled=${busy}
            @click=${() => void this._done()}
          >
            ${this._committing ? "Saving…" : "Done"}
          </button>
        </div>
      </div>
    `;
  }
};
ButlerBriefModal.styles = i$3`
    :host {
      position: fixed;
      inset: 0;
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 12px;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(2px);
      box-sizing: border-box;
    }

    .dialog {
      width: min(560px, 100%);
      max-height: min(82vh, 640px);
      display: flex;
      flex-direction: column;
      background: var(--card-background-color, #1c1c1c);
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.14));
      border-radius: 14px;
      box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55);
      overflow: hidden;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }

    .header-avatar {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      flex-shrink: 0;
      border: 1px solid rgba(255, 255, 255, 0.18);
    }

    .header-titles {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .header-title {
      font-size: 0.98rem;
      font-weight: 700;
      line-height: 1.2;
    }

    .header-sub {
      font-size: 0.74rem;
      color: var(--secondary-text-color, #9e9e9e);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .close-btn {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 1.3rem;
      line-height: 1;
      cursor: pointer;
      padding: 4px 6px;
      border-radius: 6px;
    }

    .close-btn:hover {
      background: rgba(127, 127, 127, 0.18);
      color: var(--primary-text-color, #fff);
    }

    .messages {
      flex: 1 1 auto;
      overflow-y: auto;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 180px;
    }

    .msg-row {
      display: flex;
      align-items: flex-end;
      gap: 8px;
    }

    .msg-row.user {
      justify-content: flex-end;
    }

    .msg-avatar {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      flex-shrink: 0;
      border: 1px solid rgba(255, 255, 255, 0.14);
    }

    .bubble {
      max-width: 84%;
      padding: 8px 11px;
      border-radius: 12px;
      font-size: 0.86rem;
      line-height: 1.42;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .msg-row.assistant .bubble {
      background: var(--secondary-background-color, rgba(255, 255, 255, 0.07));
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.09));
      border-bottom-left-radius: 4px;
    }

    .msg-row.user .bubble {
      background: rgba(3, 169, 244, 0.2);
      border: 1px solid rgba(3, 169, 244, 0.35);
      border-bottom-right-radius: 4px;
    }

    .typing {
      color: var(--secondary-text-color, #9e9e9e);
      font-style: italic;
    }

    .error-banner {
      margin: 0 14px 8px;
      padding: 8px 10px;
      border-radius: 8px;
      background: rgba(244, 67, 54, 0.14);
      color: var(--error-color, #ef5350);
      font-size: 0.8rem;
    }

    .composer {
      display: flex;
      align-items: flex-end;
      gap: 8px;
      padding: 10px 14px;
      border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    }

    textarea {
      flex: 1 1 auto;
      resize: none;
      background: var(--secondary-background-color, rgba(255, 255, 255, 0.06));
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.18));
      border-radius: 10px;
      padding: 8px 10px;
      font-size: 0.86rem;
      font-family: inherit;
      line-height: 1.35;
      min-height: 38px;
      max-height: 110px;
      box-sizing: border-box;
    }

    textarea:focus {
      outline: none;
      border-color: var(--primary-color, #03a9f4);
    }

    .send-btn {
      background: var(--secondary-background-color, rgba(255, 255, 255, 0.1));
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.22));
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.82rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      white-space: nowrap;
    }

    .send-btn:hover:not(:disabled) {
      background: rgba(127, 127, 127, 0.22);
    }

    .send-btn:disabled {
      opacity: 0.45;
      cursor: default;
    }

    .footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 14px;
      border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      background: rgba(0, 0, 0, 0.14);
    }

    .cancel-btn {
      background: transparent;
      color: var(--secondary-text-color, #bdbdbd);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.2));
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 0.82rem;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
    }

    .cancel-btn:hover:not(:disabled) {
      background: rgba(127, 127, 127, 0.16);
      color: var(--primary-text-color, #fff);
    }

    .done-btn {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border: none;
      border-radius: 8px;
      padding: 6px 16px;
      font-size: 0.84rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
    }

    .done-btn:hover:not(:disabled) {
      opacity: 0.92;
    }

    .done-btn:disabled,
    .cancel-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }
  `;
__decorateClass$1([
  n2({ attribute: false })
], ButlerBriefModal.prototype, "hass", 2);
__decorateClass$1([
  r()
], ButlerBriefModal.prototype, "_messages", 2);
__decorateClass$1([
  r()
], ButlerBriefModal.prototype, "_pendingActions", 2);
__decorateClass$1([
  r()
], ButlerBriefModal.prototype, "_draft", 2);
__decorateClass$1([
  r()
], ButlerBriefModal.prototype, "_sending", 2);
__decorateClass$1([
  r()
], ButlerBriefModal.prototype, "_committing", 2);
__decorateClass$1([
  r()
], ButlerBriefModal.prototype, "_error", 2);
ButlerBriefModal = __decorateClass$1([
  t("butler-brief-modal")
], ButlerBriefModal);
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __decorateClass = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc(target, key) : target;
  for (var i2 = decorators.length - 1, decorator; i2 >= 0; i2--)
    if (decorator = decorators[i2])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp(target, key, result);
  return result;
};
const STORAGE_KEY_SELECTED_SPACE = "hvac_butler_card_selected_space";
const BUTLER_UPDATED_EVENT = "hvac_butler_updated";
const STARTUP_RETRY_DELAYS_MS = [2e3, 3e3, 5e3, 8e3, 1e4];
let HvacButlerCard = class extends i {
  constructor() {
    super(...arguments);
    this._config = { type: "custom:hvac-butler-card" };
    this._status = "idle";
    this._spaces = [];
    this._entries = [];
    this._latestPlan = null;
    this._selectedSpaceId = "";
    this._selectedEntry = null;
    this._showBriefModal = false;
    this._loading = true;
    this._reconnecting = false;
    this._runningPlan = false;
    this._error = null;
    this._lastWatchedFingerprint = "";
    this._fetching = false;
    this._pendingRefetch = false;
    this._unsubUpdatedEvent = null;
    this._subscribing = false;
    this._boundConnection = null;
    this._retryAttempt = 0;
    this._retryTimer = null;
    this._handleConnectionReady = () => {
      this._retryAttempt = 0;
      this._clearRetryTimer();
      if (this._unsubUpdatedEvent) {
        try {
          this._unsubUpdatedEvent();
        } catch {
        }
        this._unsubUpdatedEvent = null;
      }
      void this._ensureSubscribed();
      void this._fetchJournal();
    };
  }
  static getStubConfig() {
    return {
      type: "custom:hvac-butler-card",
      title: "HVAC Butler"
    };
  }
  setConfig(config) {
    this._config = {
      days: 2,
      ...config
    };
    if (config.space_id) {
      this._selectedSpaceId = config.space_id;
    }
  }
  getCardSize() {
    return 5;
  }
  connectedCallback() {
    super.connectedCallback();
    this._bindConnectionListener();
    void this._ensureSubscribed();
    void this._fetchJournal();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._clearRetryTimer();
    this._unbindConnectionListener();
    if (this._unsubUpdatedEvent) {
      this._unsubUpdatedEvent();
      this._unsubUpdatedEvent = null;
    }
  }
  updated(changedProps) {
    if (changedProps.has("hass") && this.hass) {
      this._bindConnectionListener();
      void this._ensureSubscribed();
      const fp = this._computeWatchedFingerprint();
      if (fp !== this._lastWatchedFingerprint) {
        this._lastWatchedFingerprint = fp;
        void this._fetchJournal();
      }
    }
  }
  _bindConnectionListener() {
    var _a2;
    const conn = ((_a2 = this.hass) == null ? void 0 : _a2.connection) ?? null;
    if (conn === this._boundConnection) return;
    this._unbindConnectionListener();
    if (conn == null ? void 0 : conn.addEventListener) {
      conn.addEventListener("ready", this._handleConnectionReady);
      this._boundConnection = conn;
    }
  }
  _unbindConnectionListener() {
    var _a2;
    if ((_a2 = this._boundConnection) == null ? void 0 : _a2.removeEventListener) {
      this._boundConnection.removeEventListener("ready", this._handleConnectionReady);
    }
    this._boundConnection = null;
  }
  _clearRetryTimer() {
    if (this._retryTimer !== null) {
      window.clearTimeout(this._retryTimer);
      this._retryTimer = null;
    }
  }
  _isTransientStartupError(err) {
    if (!err || typeof err !== "object") return true;
    const code = err.code;
    if (code === "unknown_command" || code === "not_loaded") return true;
    const msg = String(err.message || "").toLowerCase();
    return msg.includes("not currently loaded") || msg.includes("unknown command") || msg.includes("connection") || msg.includes("closed");
  }
  async _ensureSubscribed() {
    var _a2, _b;
    if (this._unsubUpdatedEvent || this._subscribing || !((_b = (_a2 = this.hass) == null ? void 0 : _a2.connection) == null ? void 0 : _b.subscribeEvents)) {
      return;
    }
    this._subscribing = true;
    try {
      const unsub = await this.hass.connection.subscribeEvents(() => {
        void this._fetchJournal();
      }, BUTLER_UPDATED_EVENT);
      if (!this.isConnected) {
        unsub();
      } else {
        this._unsubUpdatedEvent = unsub;
      }
    } catch {
    } finally {
      this._subscribing = false;
    }
  }
  _computeWatchedFingerprint() {
    var _a2;
    const states = (_a2 = this.hass) == null ? void 0 : _a2.states;
    if (!states) return "";
    const parts = [];
    for (const [eid, st] of Object.entries(states)) {
      if (!eid.startsWith("sensor.")) continue;
      const attrs = st.attributes || {};
      if (attrs.butler_schedules !== void 0 || attrs.space_summaries !== void 0 || attrs.space_explanations !== void 0) {
        parts.push(`${eid}:${st.state}@${st.last_updated}`);
      }
    }
    return parts.sort().join("|");
  }
  async _fetchJournal() {
    if (!this.hass) return;
    if (this._fetching) {
      this._pendingRefetch = true;
      return;
    }
    this._fetching = true;
    try {
      const wsMsg = {
        type: "hvac_butler/journal",
        days: this._config.days ?? 2
      };
      if (this._config.limit !== void 0) {
        wsMsg.limit = this._config.limit;
      }
      const resp = await this.hass.callWS(wsMsg);
      this._clearRetryTimer();
      this._retryAttempt = 0;
      this._reconnecting = false;
      this._status = resp.status || "idle";
      this._spaces = resp.spaces || [];
      this._entries = resp.entries || [];
      this._latestPlan = resp.latest_plan ?? null;
      this._error = null;
      this._runningPlan = this._status === "planning" || this._status === "revising";
      const validIds = /* @__PURE__ */ new Set([
        ALL_SPACES_ID,
        ...this._spaces.map((s2) => s2.space_id)
      ]);
      if (!this._selectedSpaceId || !validIds.has(this._selectedSpaceId)) {
        const stored = this._readSavedSpace();
        if (this._config.space_id && validIds.has(this._config.space_id)) {
          this._selectedSpaceId = this._config.space_id;
        } else if (stored && validIds.has(stored)) {
          this._selectedSpaceId = stored;
        } else if (this._spaces.length > 0) {
          this._selectedSpaceId = ALL_SPACES_ID;
        }
      }
    } catch (err) {
      if (this._isTransientStartupError(err) && this._retryAttempt < STARTUP_RETRY_DELAYS_MS.length) {
        const delay = STARTUP_RETRY_DELAYS_MS[this._retryAttempt++];
        this._reconnecting = true;
        this._error = null;
        this._clearRetryTimer();
        this._retryTimer = window.setTimeout(() => {
          this._retryTimer = null;
          void this._fetchJournal();
        }, delay);
      } else {
        this._reconnecting = false;
        this._error = err instanceof Error ? err.message : (err == null ? void 0 : err.message) || "Unable to load HVAC Butler journal.";
      }
    } finally {
      if (!this._reconnecting) {
        this._loading = false;
      }
      this._fetching = false;
      if (this._pendingRefetch) {
        this._pendingRefetch = false;
        void this._fetchJournal();
      }
    }
  }
  _readSavedSpace() {
    try {
      return window.localStorage.getItem(STORAGE_KEY_SELECTED_SPACE) || "";
    } catch {
      return "";
    }
  }
  _saveSelectedSpace(spaceId) {
    try {
      window.localStorage.setItem(STORAGE_KEY_SELECTED_SPACE, spaceId);
    } catch {
    }
  }
  _handleSpaceChange(ev) {
    const select = ev.target;
    this._selectedSpaceId = select.value;
    this._saveSelectedSpace(select.value);
  }
  async _handleRunPlan() {
    if (!this.hass || this._runningPlan) return;
    this._runningPlan = true;
    this._status = "planning";
    try {
      await this.hass.callWS({ type: "hvac_butler/run_plan" });
    } catch (err) {
      this._error = err instanceof Error ? err.message : "Failed to start nightly plan.";
      this._runningPlan = false;
    }
  }
  async _handleRunIntraday() {
    if (!this.hass || this._runningPlan) return;
    this._runningPlan = true;
    this._status = "revising";
    try {
      const msg = { type: "hvac_butler/run_intraday" };
      if (this._selectedSpaceId && this._selectedSpaceId !== ALL_SPACES_ID) {
        msg.space_id = this._selectedSpaceId;
      }
      await this.hass.callWS(msg);
    } catch (err) {
      this._error = err instanceof Error ? err.message : "Failed to start intraday check.";
      this._runningPlan = false;
    }
  }
  _statusPillInfo() {
    var _a2;
    switch (this._status) {
      case "planning":
        return { label: "Planning…", cls: "status-busy" };
      case "revising":
        return { label: "Revising…", cls: "status-busy" };
      case "ok":
        return { label: "OK", cls: "status-ok" };
      case "fallback":
        return {
          label: ((_a2 = this._entries[0]) == null ? void 0 : _a2.heuristic) ? "Basic" : "Fallback",
          cls: "status-fallback"
        };
      case "error":
        return { label: "Error", cls: "status-error" };
      default:
        return { label: "Idle", cls: "status-idle" };
    }
  }
  render() {
    const title = this._config.title || "HVAC Butler";
    const pill = this._statusPillInfo();
    const activeSpace = this._spaces.find(
      (s2) => s2.space_id === this._selectedSpaceId
    );
    const isBusy = this._runningPlan || this._status === "planning" || this._status === "revising";
    return b`
      <ha-card>
        <div class="butler-header">
          <div class="header-top">
            <div class="title-group">
              <span class="title">${title}</span>
              <span class="status-pill ${pill.cls}">${pill.label}</span>
            </div>
            <button
              class="call-butler-btn"
              @click=${() => {
      this._showBriefModal = true;
    }}
              title="Talk to HVAC Butler about upcoming events or schedule changes"
            >
              <img class="call-butler-avatar" src=${BUTLER_HEAD_DATA_URI} alt="" />
              <span>Call Butler</span>
            </button>
          </div>
          <div class="controls">
            ${this._spaces.length > 0 ? b`
                  <select
                    class="space-select"
                    aria-label="Select space"
                    .value=${this._selectedSpaceId}
                    @change=${this._handleSpaceChange}
                  >
                    <option
                      value=${ALL_SPACES_ID}
                      ?selected=${this._selectedSpaceId === ALL_SPACES_ID}
                    >
                      All spaces
                    </option>
                    ${this._spaces.map(
      (s2) => b`
                        <option
                          value=${s2.space_id}
                          ?selected=${s2.space_id === this._selectedSpaceId}
                        >
                          ${s2.name}
                        </option>
                      `
    )}
                  </select>
                ` : A}
            <button
              class="check-btn"
              ?disabled=${isBusy}
              @click=${this._handleRunIntraday}
              title="Run an immediate intraday presence & occupancy check"
            >
              Check Now
            </button>
            <button
              class="run-btn"
              ?disabled=${isBusy}
              @click=${this._handleRunPlan}
              title="Run macro-planner now for today and tomorrow"
            >
              ${isBusy ? "Running…" : "Run Plan"}
            </button>
          </div>
        </div>

        ${(activeSpace == null ? void 0 : activeSpace.active_preset) ? b`
              <div class="space-meta">
                <span>
                  Active preset: <strong>${activeSpace.active_preset}</strong>
                  ${activeSpace.active_preset !== "Butler" ? " (Shadow mode)" : ""}
                </span>
              </div>
            ` : A}

        ${this._error ? b`<div class="error-msg">${this._error}</div>` : A}

        ${this._loading ? b`
              <div class="loading">
                ${this._reconnecting ? "Connecting to HVAC Butler…" : "Loading Butler activity…"}
              </div>
            ` : b`
              <butler-timeline-view
                .entries=${this._entries}
                .latestPlan=${this._latestPlan}
                .selectedSpaceId=${this._selectedSpaceId}
                @select-entry=${(e2) => {
      this._selectedEntry = e2.detail.entry;
    }}
              ></butler-timeline-view>
            `}
      </ha-card>

      ${this._selectedEntry ? b`
            <butler-detail-modal
              .entry=${this._selectedEntry}
              .selectedSpaceId=${this._selectedSpaceId}
              @close-modal=${() => {
      this._selectedEntry = null;
    }}
            ></butler-detail-modal>
          ` : A}

      ${this._showBriefModal ? b`
            <butler-brief-modal
              .hass=${this.hass}
              @close-brief=${() => {
      this._showBriefModal = false;
    }}
              @brief-committed=${() => {
      void this._fetchJournal();
    }}
            ></butler-brief-modal>
          ` : A}
    `;
  }
};
HvacButlerCard.styles = i$3`
    :host {
      display: block;
    }

    ha-card {
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .butler-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px 8px;
      flex-wrap: wrap;
      padding: 0;
      margin: 0;
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--primary-text-color, #e1e1e1);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      font-size: 0.74rem;
      font-weight: 600;
      padding: 2px 9px;
      border-radius: 999px;
      white-space: nowrap;
    }

    .status-ok {
      background: rgba(52, 211, 153, 0.14);
      color: #34d399;
      border: 1px solid rgba(52, 211, 153, 0.35);
    }

    .status-busy {
      background: rgba(56, 189, 248, 0.16);
      color: #7dd3fc;
      border: 1px solid rgba(56, 189, 248, 0.35);
    }

    .status-fallback {
      background: rgba(251, 191, 36, 0.14);
      color: #fbbf24;
      border: 1px solid rgba(251, 191, 36, 0.35);
    }

    .status-error {
      background: rgba(244, 67, 54, 0.16);
      color: #f87171;
      border: 1px solid rgba(244, 67, 54, 0.35);
    }

    .status-idle {
      background: rgba(127, 127, 127, 0.14);
      color: var(--secondary-text-color, #9e9e9e);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }

    .header-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      width: 100%;
    }

    .call-butler-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(255, 255, 255, 0.06);
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.2));
      border-radius: 999px;
      padding: 3px 10px 3px 4px;
      font-size: 0.78rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
      transition: background 0.15s ease, border-color 0.15s ease;
    }

    .call-butler-btn:hover {
      background: rgba(3, 169, 244, 0.14);
      border-color: rgba(3, 169, 244, 0.45);
    }

    .call-butler-avatar {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      display: block;
    }

    .controls {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: nowrap;
      min-width: 0;
      width: 100%;
    }

    .space-select {
      background: var(--secondary-background-color, rgba(127, 127, 127, 0.12));
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.16));
      border-radius: 8px;
      padding: 4px 8px;
      font-size: 0.8rem;
      font-family: inherit;
      cursor: pointer;
      min-width: 0;
      flex: 1 1 auto;
      text-overflow: ellipsis;
    }

    .run-btn {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border: none;
      border-radius: 8px;
      padding: 5px 10px;
      font-size: 0.78rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
      transition: opacity 0.15s ease;
    }

    .run-btn:hover:not(:disabled) {
      opacity: 0.9;
    }

    .run-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }

    .check-btn {
      background: transparent;
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.22));
      border-radius: 8px;
      padding: 4px 9px;
      font-size: 0.78rem;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
      transition: background 0.15s ease, opacity 0.15s ease;
    }

    .check-btn:hover:not(:disabled) {
      background: rgba(127, 127, 127, 0.14);
    }

    .check-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }

    .space-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.78rem;
      color: var(--secondary-text-color, #9e9e9e);
      margin-top: -4px;
    }

    .error-msg {
      padding: 10px 12px;
      border-radius: 8px;
      background: rgba(244, 67, 54, 0.14);
      color: var(--error-color, #ef5350);
      font-size: 0.85rem;
    }

    .loading {
      padding: 20px 0;
      text-align: center;
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 0.88rem;
    }
  `;
__decorateClass([
  n2({ attribute: false })
], HvacButlerCard.prototype, "hass", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_config", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_status", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_spaces", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_entries", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_latestPlan", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_selectedSpaceId", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_selectedEntry", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_showBriefModal", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_loading", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_reconnecting", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_runningPlan", 2);
__decorateClass([
  r()
], HvacButlerCard.prototype, "_error", 2);
HvacButlerCard = __decorateClass([
  t("hvac-butler-card")
], HvacButlerCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "hvac-butler-card",
  name: "HVAC Butler Activity Card",
  description: "Space-scoped timeline of HVAC Butler daily plans and intraday evaluations with full AI commentary and schedule diffs.",
  preview: true,
  getEntitySuggestion: (hass, entityId) => {
    var _a2, _b;
    const attrs = (_b = (_a2 = hass == null ? void 0 : hass.states) == null ? void 0 : _a2[entityId]) == null ? void 0 : _b.attributes;
    if (!entityId.startsWith("sensor.") || !attrs || attrs.butler_schedules === void 0 && attrs.space_summaries === void 0 && attrs.space_explanations === void 0) {
      return null;
    }
    return {
      config: {
        type: "custom:hvac-butler-card",
        entity: entityId
      }
    };
  }
});
//# sourceMappingURL=hvac-butler-cards.js.map
