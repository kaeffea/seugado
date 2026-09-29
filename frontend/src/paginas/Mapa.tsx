import { useCallback, useEffect, useState, useRef } from "react";
import { MapContainer, TileLayer, Polygon, Tooltip, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "@geoman-io/leaflet-geoman-free";
import { useFazenda } from "../lib/fazenda";
import { api, ErroApi } from "../lib/api";
import type { Piquete, Cultivar, PlanoManejo, GeoJsonPolygon } from "../lib/tipos";
import "./Mapa.css";

// O Leaflet pinta em SVG e não entende var(--x): lemos o valor da variável do tema.
function corDoTema(variavel: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(variavel).trim();
}

function ControlesMapa({
  piquetes,
  aoCriar
}: {
  piquetes: Piquete[];
  aoCriar: (geoJson: GeoJsonPolygon) => void;
}) {
  const map = useMap();
  const inicializado = useRef(false);

  useEffect(() => {
    map.pm.addControls({
      position: "topleft",
      drawPolygon: true,
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawRectangle: false,
      drawCircle: false,
      drawText: false,
      editMode: false,
      dragMode: false,
      cutPolygon: false,
      removalMode: false,
      rotateMode: false,
    });

    const onDrawCreate = (e: any) => {
      const layer = e.layer;
      const geoJson = layer.toGeoJSON().geometry;
      map.removeLayer(layer);
      aoCriar(geoJson);
    };

    map.on("pm:create", onDrawCreate);

    return () => {
      map.pm.removeControls();
      map.off("pm:create", onDrawCreate);
    };
  }, [map, aoCriar]);

  useEffect(() => {
    if (!inicializado.current) {
      if (piquetes.length > 0) {
        const coordsParaBounds: [number, number][] = piquetes.flatMap((p) =>
          p.geometria.coordinates[0].map((coord) => [coord[1], coord[0]] as [number, number])
        );
        const bounds = L.latLngBounds(coordsParaBounds);
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [20, 20], maxZoom: 18 });
        }
      } else {
        map.setView([-14.2, -51.9], 4);
      }
      inicializado.current = true;
    }
  }, [map, piquetes]);

  return null;
}

function ControlesTopRight() {
  const map = useMap();
  const [coordsStr, setCoordsStr] = useState("");

  const irPara = () => {
    const p = coordsStr.split(",");
    if (p.length === 2) {
      const lat = parseFloat(p[0].trim());
      const lng = parseFloat(p[1].trim());
      if (!isNaN(lat) && !isNaN(lng)) {
        map.setView([lat, lng], 18);
      }
    }
  };

  const minhaLocalizacao = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        map.setView([pos.coords.latitude, pos.coords.longitude], 18);
      });
    }
  };

  return (
    <div className="controles-topo">
      <input 
        type="text" 
        placeholder="-9.78, -36.09" 
        value={coordsStr}
        onChange={(e) => setCoordsStr(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && irPara()}
      />
      <button onClick={irPara}>Ir</button>
      <button onClick={minhaLocalizacao}>Minha localização</button>
    </div>
  );
}

export default function Mapa() {
  const { fazenda } = useFazenda();
  const [piquetes, setPiquetes] = useState<Piquete[]>([]);
  const [cultivares, setCultivares] = useState<Cultivar[]>([]);
  const [plano, setPlano] = useState<PlanoManejo | null>(null);
  const [semPlano, setSemPlano] = useState(false);

  const [novoPiqueteGeometria, setNovoPiqueteGeometria] = useState<GeoJsonPolygon | null>(null);
  const [nome, setNome] = useState("");
  const [cultivarId, setCultivarId] = useState("");
  const [alturaCm, setAlturaCm] = useState("");
  const [dataMedida, setDataMedida] = useState(() => new Date().toISOString().split("T")[0]);

  const [editandoFormaId, setEditandoFormaId] = useState<string | null>(null);
  const [piqueteSelecionadoId, setPiqueteSelecionadoId] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const layerRefs = useRef(new Map<string, L.Polygon>());

  const [confirmarDesativacaoId, setConfirmarDesativacaoId] = useState<string | null>(null);

  // Incrementing it reloads piquetes and plano (after a failed save or a cancelled edit).
  const [recarga, setRecarga] = useState(0);
  const carregarPiquetesEPlano = useCallback(() => setRecarga(n => n + 1), []);

  useEffect(() => {
    if (!fazenda) return;
    api<Cultivar[]>("/cultivares")
      .then(dados => {
        setCultivares(dados);
        const marandu = dados.find(c => c.slug === "marandu");
        if (marandu) setCultivarId(marandu.id);
      })
      .catch(console.error);
  }, [fazenda]);

  useEffect(() => {
    if (!fazenda) return;
    let cancelado = false;

    api<Piquete[]>(`/fazendas/${fazenda.id}/piquetes`)
      .then(p => {
        if (cancelado) return;
        setPiquetes(p);
        setNome(`Piquete ${p.length + 1}`);
      })
      .catch(console.error);

    api<PlanoManejo>(`/fazendas/${fazenda.id}/plano/atual`)
      .then(pl => {
        if (cancelado) return;
        setPlano(pl);
        setSemPlano(false);
      })
      .catch(e => {
        if (cancelado) return;
        if (e instanceof ErroApi && e.status === 404) {
          // Sem plano ainda: piquetes em cinza ("sem estimativa") e aviso no painel.
          setPlano(null);
          setSemPlano(true);
        } else {
          console.error(e);
        }
      });

    return () => {
      cancelado = true;
    };
  }, [fazenda, recarga]);

  const aoSalvarNovo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fazenda || !novoPiqueteGeometria) return;
    setErro(null);

    try {
      const payload = {
        nome,
        geometria: novoPiqueteGeometria,
        cultivar_id: cultivarId,
        metodo_pastejo: "rotacionado",
        altura_atual_cm: parseFloat(alturaCm),
        data_medicao: dataMedida || new Date().toISOString().split("T")[0]
      };
      
      const novo = await api<Piquete>(`/fazendas/${fazenda.id}/piquetes`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      
      setPiquetes(prev => [...prev, novo]);
      setNovoPiqueteGeometria(null);
      setAlturaCm("");
      setNome(`Piquete ${piquetes.length + 2}`);
      setPiqueteSelecionadoId(novo.id);
    } catch (err: any) {
      setErro(err instanceof ErroApi ? err.corpo : err.message);
    }
  };

  const cancelarNovo = () => {
    setNovoPiqueteGeometria(null);
    setErro(null);
  };

  const habilitarEdicaoForma = (id: string) => {
    setEditandoFormaId(id);
    const layer = layerRefs.current.get(id);
    if (layer) {
      layer.pm.enable({ allowSelfIntersection: false });
    }
  };

  const salvarForma = async (id: string) => {
    if (!fazenda) return;
    const layer = layerRefs.current.get(id);
    if (!layer) return;
    
    layer.pm.disable();
    setEditandoFormaId(null);
    setErro(null);

    const novaGeometria = layer.toGeoJSON().geometry;
    const p = piquetes.find(x => x.id === id);
    if (!p) return;

    try {
      const payload = {
        nome: p.nome,
        geometria: novaGeometria,
        cultivar_id: p.cultivar_id,
        metodo_pastejo: p.metodo_pastejo
      };
      
      const atualizado = await api<Piquete>(`/fazendas/${fazenda.id}/piquetes/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload)
      });
      
      setPiquetes(prev => prev.map(x => x.id === id ? atualizado : x));
    } catch (err: any) {
      setErro(err instanceof ErroApi ? err.corpo : err.message);
      carregarPiquetesEPlano();
    }
  };

  const cancelarForma = (id: string) => {
    const layer = layerRefs.current.get(id);
    if (layer) layer.pm.disable();
    setEditandoFormaId(null);
    carregarPiquetesEPlano();
  };

  const desativar = async (id: string) => {
    if (!fazenda) return;
    setErro(null);
    try {
      await api(`/fazendas/${fazenda.id}/piquetes/${id}`, { method: "DELETE" });
      setPiquetes(prev => prev.filter(x => x.id !== id));
      if (piqueteSelecionadoId === id) setPiqueteSelecionadoId(null);
      setConfirmarDesativacaoId(null);
    } catch (err: any) {
      setErro(err instanceof ErroApi ? err.corpo : err.message);
      setConfirmarDesativacaoId(null);
    }
  };

  const obterCor = (pId: string) => {
    if (!plano) return corDoTema("--cor-sem-estimativa");
    const resumo = plano.piquetes.find(x => x.piquete_id === pId);
    if (!resumo) return corDoTema("--cor-sem-estimativa");

    if (resumo.faltantes.length > 0 || resumo.altura_hoje_cm === null) return corDoTema("--cor-sem-estimativa");
    if (resumo.situacao === "ocupado") {
      if (resumo.altura_saida_alvo_cm !== null && resumo.altura_hoje_cm <= resumo.altura_saida_alvo_cm) return corDoTema("--cor-sair");
      return corDoTema("--cor-ocupado");
    } else {
      if (resumo.altura_entrada_alvo_cm !== null && resumo.altura_hoje_cm >= resumo.altura_entrada_alvo_cm) return corDoTema("--cor-pronto");
      return corDoTema("--cor-crescendo");
    }
  };

  return (
    <div className="mapa-container">
      <div className="mapa-wrapper" style={{ position: "relative" }}>
        <MapContainer center={[-14.2, -51.9]} zoom={4} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Tiles &copy; Esri"
            maxZoom={20}
            maxNativeZoom={19}
            className={!plano ? "mapa-cinza" : ""}
          />
          <ControlesMapa 
            piquetes={piquetes} 
            aoCriar={setNovoPiqueteGeometria} 
          />
          <ControlesTopRight />

          {piquetes.map(p => {
            const positions = p.geometria.coordinates[0].map(c => [c[1], c[0]] as [number, number]);
            const resumo = plano?.piquetes.find(x => x.piquete_id === p.id);
            const color = obterCor(p.id);

            return (
              <Polygon 
                key={p.id} 
                positions={positions} 
                color={color}
                weight={editandoFormaId === p.id ? 4 : 2}
                ref={(r) => { if (r) layerRefs.current.set(p.id, r); }}
                eventHandlers={{
                  click: () => setPiqueteSelecionadoId(p.id)
                }}
              >
                <Tooltip permanent direction="center" className="tooltip-piquete">
                  <div className="tooltip-titulo">
                    {p.nome} {resumo?.altura_hoje_cm ? `· ${resumo.altura_hoje_cm.toFixed(1)} cm` : ""}
                  </div>
                  <div className="tooltip-detalhes">
                    Capim: {p.cultivar_nome}<br/>
                    Situação: {resumo?.situacao || p.situacao}<br/>
                    {resumo?.lote_atual_nome && <>Lote: {resumo.lote_atual_nome}<br/></>}
                    {resumo?.confianca && <>Confiança: {resumo.confianca} ({resumo.motivo_confianca})</>}
                  </div>
                </Tooltip>
              </Polygon>
            );
          })}

          {plano && plano.movimentacoes.map(m => {
            if (!m.piquete_origem_id || !m.piquete_destino_id) return null;
            const orig = piquetes.find(p => p.id === m.piquete_origem_id);
            const dest = piquetes.find(p => p.id === m.piquete_destino_id);
            if (!orig || !dest) return null;

            const calcCenter = (p: Piquete): [number, number] => {
              const coords = p.geometria.coordinates[0];
              const lat = coords.reduce((acc, c) => acc + c[1], 0) / coords.length;
              const lng = coords.reduce((acc, c) => acc + c[0], 0) / coords.length;
              return [lat, lng];
            };

            const origCenter = calcCenter(orig);
            const destCenter = calcCenter(dest);
            const dataStr = new Date(m.data + "T00:00:00").toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' });

            return (
              <Polyline 
                key={m.id} 
                positions={[origCenter, destCenter]} 
                dashArray="10, 10" 
                color={corDoTema("--cor-superficie")}
                weight={3}
              >
                <Tooltip permanent direction="center" opacity={0.8}>
                  {dataStr} · {m.lote_nome}
                </Tooltip>
              </Polyline>
            );
          })}
        </MapContainer>
        
        <div className="legenda-mapa">
          <div className="legenda-item"><div className="legenda-cor sem-estimativa"></div> Sem estimativa</div>
          <div className="legenda-item"><div className="legenda-cor sair"></div> Precisa sair</div>
          <div className="legenda-item"><div className="legenda-cor ocupado"></div> Com gado</div>
          <div className="legenda-item"><div className="legenda-cor pronto"></div> Pronto para entrar</div>
          <div className="legenda-item"><div className="legenda-cor crescendo"></div> Crescendo</div>
        </div>
      </div>

      <div className="painel-lateral">
        {erro && <div className="mensagem-erro">{erro}</div>}
        
        {novoPiqueteGeometria ? (
          <div>
            <h2>Novo piquete</h2>
            <form onSubmit={aoSalvarNovo} className="formulario-piquete">
              <label>
                Nome
                <input required type="text" value={nome} onChange={e => setNome(e.target.value)} />
              </label>
              <label>
                Capim
                <select value={cultivarId} onChange={e => setCultivarId(e.target.value)} required>
                  {cultivares.filter(c => c.calibrada).map(c => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
              </label>
              <label>
                Método
                <input type="text" value="Rotacionado" disabled />
              </label>
              <label>
                Altura média medida (cm)
                <input required type="number" step="0.1" value={alturaCm} onChange={e => setAlturaCm(e.target.value)} />
              </label>
              <label>
                Data da medida
                <input required type="date" value={dataMedida} onChange={e => setDataMedida(e.target.value)} />
              </label>
              <div className="acoes-formulario">
                <button type="submit" className="botao-acao">Salvar</button>
                <button type="button" className="botao-acao secundario" onClick={cancelarNovo}>Cancelar</button>
              </div>
            </form>
          </div>
        ) : (
          <div>
            <h2>Piquetes ({piquetes.length})</h2>
            {semPlano && <p className="texto-suave">Ainda não há plano para esta fazenda</p>}
            <ul className="lista-piquetes">
              {piquetes.map(p => (
                <li 
                  key={p.id} 
                  className={`item-piquete ${piqueteSelecionadoId === p.id ? 'ativo' : ''}`}
                  onClick={() => setPiqueteSelecionadoId(p.id)}
                >
                  <h3>{p.nome}</h3>
                  <p>{p.cultivar_nome} · {p.metodo_pastejo} · {p.area_ha.toFixed(2)} ha</p>
                  <p>Situação: {p.situacao}</p>
                  {p.ultima_altura_cm && <p>Última medida: {p.ultima_altura_cm} cm</p>}
                  
                  {piqueteSelecionadoId === p.id && (
                    <div className="acoes-piquete">
                      {editandoFormaId === p.id ? (
                        <>
                          <button className="botao-acao" onClick={(e) => { e.stopPropagation(); salvarForma(p.id); }}>Salvar forma</button>
                          <button className="botao-acao secundario" onClick={(e) => { e.stopPropagation(); cancelarForma(p.id); }}>Cancelar</button>
                        </>
                      ) : confirmarDesativacaoId === p.id ? (
                        <>
                          <span className="confirmar-desativacao">Desativar mesmo?</span>
                          <button className="botao-acao perigo" onClick={(e) => { e.stopPropagation(); desativar(p.id); }}>Sim</button>
                          <button className="botao-acao secundario" onClick={(e) => { e.stopPropagation(); setConfirmarDesativacaoId(null); }}>Não</button>
                        </>
                      ) : (
                        <>
                          <button className="botao-acao secundario" onClick={(e) => { e.stopPropagation(); habilitarEdicaoForma(p.id); }}>Editar forma</button>
                          <button className="botao-acao perigo" onClick={(e) => { e.stopPropagation(); setConfirmarDesativacaoId(p.id); }}>Desativar</button>
                        </>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
