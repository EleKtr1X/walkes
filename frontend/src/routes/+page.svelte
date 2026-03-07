<script lang="ts">
  import mbgl from 'mapbox-gl';
  const { Map } = mbgl;
  import 'mapbox-gl/dist/mapbox-gl.css';
	import { onDestroy, onMount } from 'svelte';
  import { PUBLIC_MAPBOX_GL } from '$env/static/public';

  let map: mapboxgl.Map;
  let mapContainer: HTMLElement;
  let lat, lng, zoom;

  lat = 43.4697944;
  lng = -80.5537445
  zoom = 15;

  let init = {lng, lat, zoom};

  onMount(() => {
    map = new Map({
      container: mapContainer,
      accessToken: PUBLIC_MAPBOX_GL,
      center: [init.lng, init.lat],
      zoom: init.zoom,
    });
  })

  onDestroy(() => {
    if (map) {
      map.remove();
    }
  })
</script>

<div class="absolute w-full h-full" bind:this={mapContainer}></div>