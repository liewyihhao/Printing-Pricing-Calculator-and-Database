"use client";

import Link from "next/link";
import { ShoppingCart, Menu, X, ChevronDown, Globe } from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useCartStore } from "@/stores/cart";
import { Button } from "@/components/ui/button";

const CATEGORIES: { label: string; href: string }[] = [
  { label: "All products", href: "/products" },
  { label: "Business Cards", href: "/products?category=Cards" },
  { label: "Flyers & Brochures", href: "/products?category=Marketing+%26+Signage" },
  { label: "Stickers & Labels", href: "/products?category=Stickers+%26+Labels" },
  { label: "Booklets & Books", href: "/products?category=Books+%26+Pads" },
  { label: "Banners & Signage", href: "/products?category=Marketing+%26+Signage" },
  { label: "Packaging & Bags", href: "/products?category=Packaging+%26+Bags" },
  { label: "Calendars", href: "/products?category=Calendars" },
  { label: "Promo & Gifts", href: "/products?category=Promo+%26+Gifts" },
];

const NAV_LINKS = [
  { label: "Templates", href: "/templates" },
  { label: "Track Order", href: "/track" },
];

const REGIONS = ["MY", "SG", "BN"];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [region, setRegion] = useState("MY");
  const itemCount = useCartStore((s) => s.itemCount());

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-300 bg-white border-b border-border",
        scrolled ? "shadow-sm" : ""
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-6">
          {/* Logo */}
          <Link href="/" className="flex items-center shrink-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="Printoka" className="h-8 w-auto" />
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {/* Products dropdown (hover) */}
            <div className="relative group">
              <Link
                href="/products"
                className="flex items-center gap-1 px-3 py-2 rounded-md text-sm font-medium text-ink-secondary hover:text-ink hover:bg-surface-subtle transition-colors"
              >
                Products
                <ChevronDown className="w-3.5 h-3.5 transition-transform group-hover:rotate-180" />
              </Link>
              <div className="absolute left-0 top-full pt-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-50">
                <div className="w-60 rounded-md border border-border bg-white shadow-panel py-2">
                  {CATEGORIES.map((c) => (
                    <Link
                      key={c.label}
                      href={c.href}
                      className="block px-4 py-2 text-sm text-ink-secondary hover:text-brand-500 hover:bg-surface-subtle transition-colors"
                    >
                      {c.label}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href + link.label}
                href={link.href}
                className="px-3 py-2 rounded-md text-sm font-medium text-ink-secondary hover:text-ink hover:bg-surface-subtle transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            {/* Cart */}
            <Link href="/cart" className="relative">
              <Button variant="ghost" size="icon-sm">
                <ShoppingCart className="w-4.5 h-4.5" />
              </Button>
              {itemCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4.5 h-4.5 bg-brand-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {itemCount > 9 ? "9+" : itemCount}
                </span>
              )}
            </Link>

            {/* Country selector */}
            <div className="hidden sm:block relative group">
              <button className="flex items-center gap-1 px-2.5 py-1.5 rounded-sm border border-border text-sm font-medium text-ink-secondary hover:border-border-strong">
                <Globe className="w-4 h-4" />
                {region}
                <ChevronDown className="w-3.5 h-3.5" />
              </button>
              <div className="absolute right-0 top-full pt-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                <div className="w-24 rounded-md border border-border bg-white shadow-panel py-1">
                  {REGIONS.map((r) => (
                    <button
                      key={r}
                      onClick={() => setRegion(r)}
                      className={cn(
                        "block w-full text-left px-3 py-1.5 text-sm hover:bg-surface-subtle",
                        r === region ? "text-brand-500 font-semibold" : "text-ink-secondary"
                      )}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="hidden sm:flex items-center gap-2">
              <Link href="/auth/login">
                <Button variant="ghost" size="sm">
                  Sign in
                </Button>
              </Link>
              <Link href="/auth/register">
                <Button size="sm">Get started</Button>
              </Link>
            </div>

            {/* Mobile menu toggle */}
            <button
              className="md:hidden p-2 rounded-md text-ink-secondary hover:text-ink hover:bg-surface-subtle"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-border bg-white">
          <nav className="flex flex-col p-4 gap-1">
            <Link
              href="/products"
              className="px-3 py-2.5 rounded-md text-sm font-semibold text-ink hover:bg-surface-subtle"
              onClick={() => setMobileOpen(false)}
            >
              All products
            </Link>
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href + link.label}
                href={link.href}
                className="px-3 py-2.5 rounded-md text-sm font-medium text-ink hover:bg-surface-subtle"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            <div className="border-t border-border mt-2 pt-2 flex flex-col gap-2">
              <Link href="/auth/login" onClick={() => setMobileOpen(false)}>
                <Button variant="outline" size="md" className="w-full">
                  Sign in
                </Button>
              </Link>
              <Link href="/auth/register" onClick={() => setMobileOpen(false)}>
                <Button size="md" className="w-full">
                  Get started
                </Button>
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
