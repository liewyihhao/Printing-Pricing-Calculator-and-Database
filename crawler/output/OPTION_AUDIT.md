# Excard option-parity audit — every control, first field → Delivery

_price relationship: **AXIS** = changes price (must be sampled), **neutral** = present but price-independent, **delivery** = affects shipping fee only._

## arch-file

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**Quantity**
- `select` **ddlQuantityLast** [?] — - Please Select -, 20, 40, 60, 80, 100, 200, 300 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## banner

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Standard Size** [?] — Standard Size, Custom Size
- `radio` **Landscape** [?] — Landscape, Portrait
- `select` **ddlSize** [?] — - Please Select -, 3ft x 2ft, 4ft x 2ft, 6ft x 2ft, 4ft x 3ft, 8ft x 3ft, 10ft x 3ft, 8ft x 4ft …
- `select` **ddlPaper** [?] — - Please Select -, Tarpaulin 300gsm, Tarpaulin 380gsm
- `select` **ddlTopEyelet** [?] — - Please Select -, 2, 3, 4, 5
- `select` **ddlBottomEyelet** [?] — - Please Select -, 2, 3, 4, 5
- `select` **ddlQuantity** [?] — - Please Select -, 1, 2, 3, 4, 5, 6, 7 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## bill-book

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **Size *** [?] — -- Select Size --, 145mm × 210mm, (A4) 210mm × 297mm, (B5) 176mm × 250mm, (B4) 250mm × 353mm, 90mm × 140mm, 90mm × 177mm, 95mm × 210mm …

**Binding Type * Book Pad**
- `radio` **Binding Type *** [?] — book, pad
- `radio` **Orientation *** [?] — landscape, portrait
- `radio` **Binding Location *** [?] — left, top

**Layers Configuration**
- `radio` **Paper Materials *** [?] — ncr, normal
- `select` **Paper Material + Layers *** [?] — -- Select Paper Material + Layers --, NCR - 2 Layers, NCR - 3 Layers, NCR - 4 Layers, NCR - 5 Layers, NCR - 6 Layers
- `radio` **Last Layer Perforation *** [?] — no, yes
- `select` **paperLayer1** [?] — - Please Select -, NCR White 50gsm, NCR Green 50gsm, NCR Blue 50gsm, NCR Yellow 50gsm, NCR Pink 50gsm

**Print Color**
- `select` **Print Colour *** [?] — -- Select Print Colour --, 1C (Front), 2C (Front), 4C (Front), 1C (Both), 2C (Front) / 1C (Back), 4C (Front) / 1C (Back)

**Quantity**
- `select` **Quantity (Books / Pads) *** [?] — -- Select Quantity --, 10, 20, 30, 40, 50, 60, 70 …
- `select` **Sets per Book/Pad *** [?] — 50 Sets

**Finishing**
- `radio` **Number From** [?] — no, yes
- `input` **Number From** [?] — 
- `input` **Number To** [?] — 
- `radio` **Hole Punching** [?] — no, yes

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## booklet
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## bookmark

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 250gsm, Gloss Art Card 310gsm, Linen 240gsm, Metal Ice 250gsm, Super White 250gsm, Suwen 240gsm, Synthetic Paper 180micron
- `radio` **4C (Front)** [?] — 4C (Front), 4C (Both)
- `select` **ddlFinishing** [?] — - Please Select -, Gloss Lamination (Both), Matte Lamination (Both), Matte Lamination (Both) + Spot UV (Front), No Required
- `select` **ddlQuantity** [?] — - Please Select -, 100, 200, 300, 500, 1000, 2000, 3000 …

**Optional Finishing**
- `radio` **No Required** [?] — No Required, Round Corner
- `radio` **No Required** [?] — No Required, Hole Punching (6mm)

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## brochure
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## bunting

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Bunting** [?] — Bunting, Bunting (Gear X Stand), Bunting (Round Base Stand), Bunting (Tripod Stand)
- `select` **ddlSize** [?] — - Please Select -, 2ft x 5ft, 2ft x 6ft, 2.5ft x 6ft
- `select` **ddlPaper** [?] — - Please Select -, Tarpaulin 300gsm, Synthetic Paper 180micron
- `radio` **720 dpi solvent** [?] — 720 dpi solvent, 1440 dpi solvent
- `select` **ddlFinishing** [?] — - Please Select -, Come With PVC Pipe, Come With Wood and Pre-Installed Wire (No18), Come With Wood Only
- `select` **ddlQuantity** [?] — - Please Select -, 1, 2, 3, 4, 5, 6, 7 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## business-card

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Category *** [?] — standard, thin_fold, fat_fold, custom_die_cut, plastic_card
- `select` **Size *** [?] — -- Select Size --, 54mm × 89mm, 52mm × 86mm, 50mm × 89mm, 54mm × 86mm, Other (Custom Size)
- `radio` **Orientation *** [?] — landscape, portrait
- `select` **Paper *** [?] — -- Select Paper --, Gloss Art Card 250gsm (2 side coated), Gloss Art Card 310gsm (2 side coated), Gloss Art Card 360gsm (2 side coated), Matte Art Card 250gsm, Linen 240gsm, Metal Ice 250gsm, Synthetic Paper 180micron (0.18mm) …

**Print Colour * 4C (Both) 4C (Front)**
- `select` **Print Colour *** [?] — 4C (Both), 4C (Front)
- `select` **Silkscreen Spot UV *** [?] — No Required
- `select` **Quantity *** [?] — -- Select Quantity --, 50, 100, 200, 300 — Best Seller, 400, 500 — Best Seller, 600 …
- `select` **Package *** [?] — Normal (1 Design), 2 In 1 (2 Designs), 3 In 1 (3 Designs), 4 In 1 (4 Designs), 5 In 1 (5 Designs), 6 In 1 (6 Designs), 7 In 1 (7 Designs), 8 In 1 (8 Designs) …

**Optional Finishing**
- `select` **Hot Stamping** [?] — No Hot Stamping, 1C (Front), 1C (Back), 2C (Front), 2C (Back)
- `radio` **Round Corner** [?] — no, required
- `radio` **Hole Punching** [?] — no, 3mm, 5mm

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## button-badge

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlPackage** [?] — - Please Select -, Normal, 2in1, 3in1, 4in1, 5in1

**Gloss Art Paper 150gsm**
- `select` **ddlQuantity** [?] — - Please Select -, 10, 20, 30, 40, 50, 60, 70 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## canvas-tote-bag

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Silkscreen Tote Bag ( 1C )** [?] — Silkscreen Tote Bag ( 1C ), Heat Transfer Tote Bag ( 4C ), DTF Tote Bag With Zip
- `select` **ddlPrintColour** [?] — 1C (Front), 1C (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 100, 200, 300, 400, 500, 600, 700 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## car-sticker

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlSize** [?] — - Please Select -, 54mm x 89mm, 75mm x 75mm, 100mm x 100mm, 110mm x 90mm, 115mm x 120mm, 130mm x 170mm, 165mm x 90mm …
- `radio` **Face Out View** [?] — Face Out View, Face In View, Both Side View
- `select` **ddlQuantity** [?] — - Please Select -, 10, 20, 50, 100, 200, 300, 400 …

**Other Finishing**
- `select` **ddlCoverVDPType** [?] — - Please Select -, Not Required, Variable Data Printing (VDP)

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## computer-form

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## customprint
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## desk-calendar-hard-stand
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## desk-calendar-soft-stand
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## envelope

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlQuantity** [?] — - Please Select -, 1000, 2000, 3000, 4000, 5000, 10000, 15000 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## flyer
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## folder

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Presentation Folder** [?] — Presentation Folder, Document Folder, Key Folder, CD Jacket
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 250gsm (1 side coated), Gloss Art Card 300gsm (1 side coated), Gloss Art Card 250gsm (2 side coated), Gloss Art Card 310gsm (2 side coated), Gloss Art Card 360gsm (2 side coated)
- `radio` **4C (Front)** [?] — 4C (Front), 4C (Both)
- `select` **ddlLamination** [?] — - Please Select -, Gloss Lamination (Front), Gloss Lamination (Both), Matte Lamination (Front), Matte Lamination (Front) + Spot UV (Front), Matte Lamination (Both), Matte Lamination (Both) + Spot UV (Front), Gloss Waterbase Varnish (Front) …
- `select` **ddlQuantity** [?] — - Please Select -, 250, 300, 350, 400, 450, 500, 1000 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## hand-fan

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 310gsm, Gloss Art Card 360gsm
- `select` **ddlFinishing** [?] — - Please Select -, Gloss Lamination (Both), Matte Lamination (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 50, 100, 150, 200, 250, 300, 350 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## hanger

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 310gsm (2 sides coated), Gloss Art Card 360gsm (2 sides coated)
- `select` **ddlPrintColour** [?] — - Please Select -, 4C (Front), 4C (Both)
- `select` **ddlLamination** [?] — - Please Select -, Matte Lamination (Both), Gloss Lamination (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 50, 100, 150, 200, 250, 300, 350 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## hard-cover-menu

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Cover + Content** [?] — Cover + Content, Cover only, Content only
- `select` **ddlFinishing** [?] — - Please Select -, Gloss Lamination (Both), Matte Lamination (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 10, 20, 30, 40, 50, 60, 70 …

**Gloss Art Paper 150gsm**
- `select` **ddlContentPage** [?] — - Please Select -, 12, 16, 20, 24, 28, 32

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## kad-kahwin

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Standard Kad Kahwin** [?] — Standard Kad Kahwin, Custom Die Cut Kad Kahwin
- `select` **ddlSize** [?] — - Please Select -, DL (99mm x 210mm), 2DL (198mm x 210mm), A4 (210mm x 297mm), A5 (148mm x 210mm), A6 (105mm x 148mm), A7 (74mm x 105mm), Square (140mm x 280mm)
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 230gsm (2 sides coated), Gloss Art Card 260gsm (2 sides coated), Gloss Art Card 310gsm (2 sides coated), Gloss Art Card 360gsm (2 sides coated), Super White 240gsm, Metal Ice 250gsm, Linen 240gsm …
- `select` **ddlPrintColour** [?] — - Please Select -, 4C (Front), 4C (Both)
- `select` **ddlLamination** [?] — - Please Select -, Not Required, Gloss Lamination (Front), Gloss Lamination (Both), Matte Lamination (Front), Matte Lamination (Both)

**Optional Finishing**
- `select` **ddlCoverHotStampingColour** [?] — Not Required, 1C (Front), 1C (Back), 2C (Front), 2C (Back)
- `select` **ddlEnvelope** [?] — - Please Select -, Not Required, White (A5), White (A6), White (DL), Pink (A5), Pink (A6), Pink (DL)

**Quantity**
- `select` **ddlQuantityLast** [?] — - Please Select -, 10, 20, 30, 40, 50, 100, 150 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## kad-terima-kasih

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlSize** [?] — - Please Select -, 40mm x 70mm, 40mm x 86mm, 52mm x 52mm
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 230gsm (2 sides coated), Gloss Art Card 260gsm (2 sides coated), Gloss Art Card 310gsm (2 sides coated), Gloss Art Card 360gsm (2 sides coated), Super White 240gsm, Vellum 220gsm, Metal Ice 250gsm
- `select` **ddlPrintColour** [?] — - Please Select -, 4C (Front), 4C (Both)
- `select` **ddlLamination** [?] — - Please Select -, Not Required, Gloss Lamination (Front), Gloss Lamination (Both), Matte Lamination (Front), Matte Lamination (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 50, 100, 150, 200, 250, 300, 350 …

**Optional Finishing**
- `radio` **Not Required** [?] — Not Required, Hole Punching (3mm)

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## kotak-cenderahati

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 260gsm (1 sides coated), Gloss Art Card 300gsm (1 sides coated), Gloss Art Card 310gsm (2 sides coated), Metal Ice 250gsm
- `select` **ddlLamination** [?] — - Please Select -, Not Required, Matte Lamination (Front), Gloss Lamination (Front), UV Varnish (Front), Gloss Waterbase Varnish (Front)
- `select` **ddlQuantity** [?] — - Please Select -, 50, 100, 150, 200, 250, 300, 350 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## l-shape-folder
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## label-sticker-with-hot-stamping
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## letterhead

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlPaper** [?] — - Please Select -, Simili 80gsm, Simili 100gsm, Conqueror 100gsm Brilliant White Laid, Conqueror 100gsm Diamond White Laid, Conqueror 100gsm White Wove, Conqueror 100gsm Cream Laid
- `select` **ddlPrintColour** [?] — 1C (Front), 2C (Front), 4C (Front), 4C (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 500, 600, 700, 800, 900, 1000, 1100 …
- `radio` **Loose** [?] — Loose, Pad (100 pcs per pad)

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## loose-sheet
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## magnet
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## mask-keeper
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## money-packet

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Standard** [?] — Standard, Premium, Hot Stamping, Pouch
- `radio` **Custom Made Money Packet** [?] — Custom Made Money Packet, Ready Designed with Editor
- `radio` **No** [?] — No, Yes
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Paper 130gsm, Linen 140gsm, Art Paper 157gsm
- `radio` **5pcs / Pack** [?] — 5pcs / Pack, 6pcs / Pack, 8pcs / Pack, 10pcs / Pack
- `select` **ddlFinishing** [?] — - Please Select -, N/A, Matte Lamination, Soft Touch Lamination
- `select` **ddlQuantity** [?] — - Please Select -, 600, 1250, 2500, 5000, 10000, 15000, 20000 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## mug

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlQuantity** [?] — - Please Select -, 20, 40, 60, 80, 100, 200, 300 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## non-woven-bag

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlBagColour** [?] — - Please Select -, Black, White, Yellow, Red, Green, Royal Blue
- `select` **ddlPrintColour** [?] — 1C (Front), 1C (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 100, 200, 300, 400, 500, 600, 700 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## notepad

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 260gsm (2 sides coated), Gloss Art Card 310gsm (2 sides coated)
- `select` **ddlLamination** [?] — - Please Select -, Matte Lamination (Both), Matte Lamination (Both) + Spot UV (Front Cover)
- `select` **ddlQuantity** [?] — - Please Select -, 250, 300, 500, 1000, 2000, 3000, 4000 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## papan-kopi

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlFinishing** [?] — SB 01
- `select` **ddlQuantity** [?] — - Please Select -, 1000, 2000, 3000, 4000, 5000, 6000, 7000 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## paper-bag

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**> Paper Bag**
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 190gsm, Gloss Art Paper 157gsm
- `select` **ddlLamination** [?] — - Please Select -, Gloss Lamination, Matte Lamination, Matte Lamination + Spot UV
- `select` **ddlRopeColour** [?] — - Please Select -, Black, Blue, Gold, Green, Red, Silver, White
- `select` **ddlCoverHotStampingColour** [?] — Not Required, 100mm x 100mm, 100mm x 200mm, 200mm x 200mm, 300mm x 100mm, 300mm x 200mm, 400mm x 100mm, 400mm x 200mm
- `select` **ddlQuantityLast** [?] — - Please Select -, 50, 100, 200, 300, 500, 600, 700 …

**DELIVERY**
- `checkbox` **Rush Order Terms & Conditions apply** [?] — 
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## pillow
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## pre-inked-stamp
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## pvc-card

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Portrait** [?] — Portrait, Landscape
- `select` **ddlPrintColour** [?] — - Please Select -, 4C (Front), 4C (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 20, 40, 60, 80, 100, 200, 300 …

**Other Finishing**
- `select` **ddlCoverVDPType** [?] — - Please Select -, Not Required, Variable Data Printing (Front), Variable Data Printing (Back), Variable Data Printing (Both)

**Optional Finishing**
- `radio` **Not Required** [?] — Not Required, Hole Punching

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## roll-form-sticker

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Sample Proof (2pcs)** [?] — no, yes
- `radio` **Category *** [?] — rectangle_square, round, custom_shape
- `input` **height** [?] — 
- `input` **width** [?] — 
- `select` **Paper *** [?] — White PP, Transparent OPP, Mirror Kote, Printing Paper, Synthetic Paper, Hologram

**Print Colour * 4C**
- `select` **Print Colour *** [?] — 4C
- `select` **Lamination / Finishing *** [?] — Not Required, Matte Lamination, Gloss Lamination, UV Varnish
- `select` **Hot Stamping Colour** [?] — Not Required, 1C (Front)

**Paper Core * 25mm 40mm 76mm**
- `select` **Paper Core *** [?] — 25mm, 40mm, 76mm
- `select` **Quantity (pcs) *** [?] — -- Select Quantity --, 1,000, 2,000, 3,000, 4,000, 5,000, 6,000, 7,000 …
- `select` **Pcs / Roll *** [?] — -- Select Pcs / Roll --, 500, 1,000, 2,000, 2,500, 5,000, 10,000

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## roll-up-stand

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**Synthethic Paper 180 micron**
- `select` **ddlFinishing** [?] — - Please Select -, Gloss Lamination, Matte Lamination
- `select` **ddlQuantity** [?] — - Please Select -, 1, 2, 3, 4, 5, 6, 7 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## sachet-board
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## Stamp-chop

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## standing-pouch

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlPaper** [?] — - Please Select -, Metalised Pet Film, Transparent Pet Film
- `select` **ddlLamination** [?] — - Please Select -, Matte Lamination (Both), Gloss Lamination (Both)
- `select` **ddlQuantity** [?] — - Please Select -, 100, 200, 300, 400, 500, 600, 700 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## static-cling-window-sticker
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## sublimation-shirt
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## tent-card

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlFinishing** [?] — - Please Select -, Matte Lamination (Both), Matte Lamination (Both) + Spot UV (Front)
- `select` **ddlQuantity** [?] — - Please Select -, 300, 500, 1000, 2000, 3000, 4000, 5000 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## voucher
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## wall-calendar

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `select` **ddlQuantity** [?] — - Please Select -, 1000, 1500, 2000, 3000, 4000, 5000, 6000 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## Wire-O-Notebook
> ⚠️ v4 page 500 (Runtime Error) — use www /spec form for this product

## wire-o-wall-calendar

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**Gloss Art Paper 150gsm**
- `select` **ddlQuantity** [?] — - Please Select -, 100, 200, 300, 500, 1000, 1500, 2000 …

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)

## wobbler

**(top)**
- `select` **(unnamed)** [?] — Track Order, Product

**General**
- `radio` **Rectangle** [?] — Rectangle, Custom Die-Cut
- `radio` **Portrait** [?] — Portrait, Landscape
- `select` **ddlPaper** [?] — - Please Select -, Gloss Art Card 260gsm, Gloss Art Card 310gsm, Gloss Art Card 360gsm
- `select` **ddlFinishing** [?] — - Please Select -, Gloss Lamination (Front), Matte Lamination (Front), Soft Touch Lamination (Front)
- `select` **ddlQuantity** [?] — - Please Select -, 50, 100, 150, 200, 250, 300, 350 …

**Optional Finishing**
- `radio` **No** [?] — No, Yes

**DELIVERY**
- `radio` **West Malaysia** [?] — West Malaysia, East Malaysia, Singapore, Thailand (Bangkok only)
- `radio` **Others Countries** [?] — Others Countries
- `select` **Others Countries** [?] — Afghanistan, Armenia, Australia, Bhutan, Brunei, Cambodia, China, Egypt …
- `radio` **Appointed Courier (Fee applies)** [?] — Appointed Courier (Fee applies), Skynet (Fee applies)
