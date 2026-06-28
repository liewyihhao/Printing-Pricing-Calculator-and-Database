import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function CTABanner() {
  return (
    <section className="py-24 bg-white">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
        <div className="bg-brand-600 rounded-3xl p-12 relative overflow-hidden">
          {/* Background pattern */}
          <div
            className="absolute inset-0 opacity-10"
            style={{
              backgroundImage:
                "radial-gradient(circle at 20% 50%, white 1px, transparent 1px), radial-gradient(circle at 80% 50%, white 1px, transparent 1px)",
              backgroundSize: "40px 40px",
            }}
          />
          <div className="relative">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4 tracking-tight">
              Ready to print?
            </h2>
            <p className="text-brand-200 text-lg mb-8 max-w-xl mx-auto">
              Join thousands of businesses who trust Printoka for their
              printing needs. Get an instant quote in under a minute.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link href="/products">
                <Button
                  size="lg"
                  className="bg-white text-brand-600 hover:bg-brand-50 rounded-xl shadow-sm"
                >
                  Browse products <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
              <Link href="/auth/register">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-brand-400 text-white hover:bg-brand-700 rounded-xl"
                >
                  Create free account
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
