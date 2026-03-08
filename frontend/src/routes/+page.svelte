<script lang="ts">
  import mbgl, { type GeoJSONSource } from 'mapbox-gl';
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
  let timer: NodeJS.Timeout | undefined = $state();

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
      if (timer) {
        clearInterval(timer);
      }

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

      timer = setInterval(async () => {
        const res = await fetch('http://localhost:8000/segments');
        const data: GeoJSON = await res.json();

        const source: GeoJSONSource = map.getSource('segments')!;
        source.setData(data);
      }, 5000)
    });
  });

  onDestroy(() => {
    if (map) {
      map.remove();
    }
    if (timer) {
      clearInterval(timer);
    }
  });

  function reportClick() {
    showOptions = !showOptions;
  }

  async function reportHazard(condition: string) {
    const res = await fetch('http://localhost:8000/report', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        condition,
        severity: 'medium',
        lat,
        lng,
      }),
    });


    if (!res.ok) {
      alert(`ERROR ${res.status}: ${res.statusText}`);
    }
  }
</script>

<div class="absolute w-full h-full" bind:this={mapContainer}></div>

<div class="flex flex-col absolute top-5 left-5">
  <input class="bg-white p-3 rounded-t-xl" type="text" placeholder="🔵 Starting point"/>
  <input class="bg-white p-3 rounded-b-xl" type="text" placeholder="📍 Destination"/>
  <button class="bg-blue-600 text-white font-bold text-2xl cursor-pointer
                 rounded-xl mt-2 py-2 hover:brightness-80">Go!</button>
</div>

<div class="flex flex-col absolute right-10 bottom-10 gap-4 items-end">
  {#if showOptions}
    <div class="bg-gray-700 p-6 rounded-2xl flex flex-row gap-3">
      <div class="flex flex-col justify-center gap-1 items-center">
        <button class="rounded-full bg-white text-white text-2xl font-bold
                      bottom-10 w-16 h-16 cursor-pointer hover:brightness-80"
                      onclick={() => reportHazard('snow')}>❄️</button>
        <span class="text-white">Snow/Ice</span>
      </div>
      <div class="flex flex-col justify-center gap-1 items-center">
        <button class="rounded-full bg-blue-600 text-white text-2xl font-bold
                      bottom-10 w-16 h-16 cursor-pointer hover:brightness-80"
                      onclick={() => reportHazard('puddle')}>💧</button>
        <span class="text-white">Puddle</span>
      </div>
      <div class="flex flex-col justify-center gap-1 items-center">
        <button class="rounded-full bg-red-600 text-white text-2xl font-bold
                      bottom-10 w-16 h-16 cursor-pointer hover:brightness-80"
                      onclick={() => reportHazard('crack')}>⚠️</button>
        <span class="text-white">Crack</span>
      </div>
      <div class="absolute bottom-16 right-6">
        <div class="w-0 h-0 -border-l-2 border-l-transparent
                            -border-r-2 border-r-transparent
                            -border-b-2 border-b-transparent
                            -border-t-2 border-t-gray-700 border-8"></div>
      </div>
    </div>
  {/if}

  <button class="rounded-full bg-blue-600 text-white text-2xl font-bold
                w-16 h-16 cursor-pointer hover:brightness-80"
                onclick={reportClick}>!</button>
</div>