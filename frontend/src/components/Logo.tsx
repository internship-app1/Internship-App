import React from 'react'
import { useResolvedTheme } from './theme-provider'
import logoDark from '../assets/logo-dark.svg'
import logoLight from '../assets/logo-light.svg'

type LogoProps = {
  /** Display size in px — the icon is square. Defaults to 24. */
  size?: number
  /** Provide a label to make the icon meaningful to screen readers (e.g. when standalone).
   *  Omit when the icon sits next to the wordmark text — it will be decorative (aria-hidden). */
  label?: string
  className?: string
}

const Logo: React.FC<LogoProps> = ({ size = 24, label, className }) => {
  const resolved = useResolvedTheme()
  return (
    <img
      src={resolved === 'dark' ? logoDark : logoLight}
      width={size}
      height={size}
      className={className}
      alt={label ?? ''}
      aria-hidden={label ? undefined : true}
      draggable={false}
    />
  )
}

export default Logo
