declare module 'react-simple-maps' {
  import { ComponentType, ReactNode } from 'react';

  export interface ComposableMapProps {
    projectionConfig?: {
      scale?: number;
      center?: [number, number];
      rotate?: [number, number, number];
    };
    projection?: string;
    className?: string;
    style?: React.CSSProperties;
    children?: ReactNode;
  }

  export interface ZoomableGroupProps {
    zoom?: number;
    center?: [number, number];
    minZoom?: number;
    maxZoom?: number;
    onMoveStart?: (event: any) => void;
    onMove?: (event: any) => void;
    onMoveEnd?: (event: any) => void;
    children?: ReactNode;
  }

  export interface GeographiesProps {
    geography: string;
    children: (data: { geographies: any[] }) => ReactNode;
  }

  export interface GeographyProps {
    key?: string;
    geography: any;
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
    onMouseEnter?: (event?: React.MouseEvent) => void;
    onMouseLeave?: (event?: React.MouseEvent) => void;
    onClick?: (event?: React.MouseEvent) => void;
    style?: {
      default?: React.CSSProperties & { cursor?: string; outline?: string; transition?: string };
      hover?: React.CSSProperties & { cursor?: string; outline?: string };
      pressed?: React.CSSProperties & { outline?: string };
    };
  }

  export interface MarkerProps {
    key?: string | number;
    coordinates: [number, number];
    onClick?: () => void;
    onMouseEnter?: () => void;
    onMouseLeave?: () => void;
    children?: ReactNode;
  }

  export const ComposableMap: ComponentType<ComposableMapProps>;
  export const ZoomableGroup: ComponentType<ZoomableGroupProps>;
  export const Geographies: ComponentType<GeographiesProps>;
  export const Geography: ComponentType<GeographyProps>;
  export const Marker: ComponentType<MarkerProps>;
}