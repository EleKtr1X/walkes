<script lang="ts">
  import mbgl from 'mapbox-gl';
  const { Map, GeolocateControl } = mbgl;
  import 'mapbox-gl/dist/mapbox-gl.css';
	import { onDestroy, onMount } from 'svelte';
  import { PUBLIC_MAPBOX_GL } from '$env/static/public';
  import type { GeoJSON } from 'geojson';

  let { data }: { data: GeoJSON } = $props();

  let map: mapboxgl.Map;
  let mapContainer: HTMLElement;
  let geo: mapboxgl.GeolocateControl;

  let lat = $state(43.4697944);
  let lng = $state(-80.5537445);
  let zoom = $state(15);
  let showOptions = $state(false);

  onMount(() => {
    map = new Map({
      container: mapContainer,
      accessToken: PUBLIC_MAPBOX_GL,
      center: [lng, lat],
      zoom: zoom,
      style: 'mapbox://styles/mapbox/dark-v11',
    });

    geo = new GeolocateControl({
      positionOptions: {
        enableHighAccuracy: true,
      },
      trackUserLocation: true,
      showUserHeading: true,
    });

    map.addControl(geo);

    map.on('load', async () => {
      geo.trigger();

      map.addSource('segments', {
        type: 'geojson',
        data: data,
      });

      map.addLayer({
        id: "segments-layer",
        type: "line",
        source: "segments",
        paint: {
          "line-color": [
            "interpolate", ["linear"], ["get", "risk_score"],
            0.0, "#00c853",
            0.5, "#ffd600",
            1.0, "#d50000"
          ],
          "line-width": 3
        }
      });

    });
  });

  onDestroy(() => {
    if (map) {
      map.remove();
    }
  });

  function reportClick() {
    showOptions = !showOptions;
  }
</script>

<div class="absolute w-full h-full" bind:this={mapContainer}></div>

<div class="flex flex-col absolute right-10 bottom-10 gap-2 items-end">
  {#if showOptions}
    <div class="bg-gray-600 p-6 rounded-2xl">
      <div class="flex flex-col justify-center gap-1">
        <button class="rounded-full bg-blue-600 text-white text-2xl font-bold
                      bottom-10 w-16 h-16 cursor-pointer">❄️</button>
        <span class="text-white">Snow/Ice</span>
      </div>
    </div>
  {/if}

  <button class="rounded-full bg-blue-600 text-white text-2xl font-bold
                w-16 h-16 cursor-pointer" onclick={reportClick}>!</button>
</div>