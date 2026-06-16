import { useEffect, useRef } from 'react'
import JsBarcode from 'jsbarcode'

/**
 * Renders a Code128 barcode entirely in the browser (no server-side image
 * generation), so it works the same locally and on Vercel.
 */
export default function Barcode({
  value,
  height = 50,
  displayValue = true,
}: {
  value: string
  height?: number
  displayValue?: boolean
}) {
  const ref = useRef<SVGSVGElement>(null)
  useEffect(() => {
    if (!ref.current || !value) return
    try {
      JsBarcode(ref.current, value, {
        format: 'CODE128',
        height,
        displayValue,
        fontSize: 13,
        margin: 4,
        width: 1.6,
      })
    } catch {
      /* invalid barcode value — leave the svg empty */
    }
  }, [value, height, displayValue])
  return <svg ref={ref} />
}
