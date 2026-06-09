const BASE = 'https://media.formula1.com/image/upload/f_auto,c_limit,q_auto,w_320/content/dam/fom-website/drivers';

const DRIVER_IMAGES = {
  antonelli:      `${BASE}/K/ANDANT01_Kimi_Antonelli/andant01.png`,
  hamilton:       `${BASE}/L/LEWHAM01_Lewis_Hamilton/lewham01.png`,
  russell:        `${BASE}/G/GEORUS01_George_Russell/georus01.png`,
  leclerc:        `${BASE}/C/CHALEC01_Charles_Leclerc/chalec01.png`,
  piastri:        `${BASE}/O/OSCPIA01_Oscar_Piastri/oscpia01.png`,
  norris:         `${BASE}/L/LANNOR01_Lando_Norris/lannor01.png`,
  max_verstappen: `${BASE}/M/MAXVER01_Max_Verstappen/maxver01.png`,
  hadjar:         `${BASE}/I/ISAHAD01_Isack_Hadjar/isahad01.png`,
  lawson:         `${BASE}/L/LIALAW01_Liam_Lawson/lialaw01.png`,
  gasly:          `${BASE}/P/PIEGAS01_Pierre_Gasly/piegas01.png`,
  bearman:        `${BASE}/O/OLIBEA01_Oliver_Bearman/olibea01.png`,
  colapinto:      `${BASE}/F/FRACOL01_Franco_Colapinto/fracol01.png`,
  arvid_lindblad: `${BASE}/A/ARVLIN01_Arvid_Lindblad/arvlin01.png`,
  sainz:          `${BASE}/C/CARSAI01_Carlos_Sainz/carsai01.png`,
  albon:          `${BASE}/A/ALEALB01_Alexander_Albon/alealb01.png`,
  ocon:           `${BASE}/E/ESTOCO01_Esteban_Ocon/estoco01.png`,
  bortoleto:      `${BASE}/G/GABBOR01_Gabriel_Bortoleto/gabbor01.png`,
  perez:          `${BASE}/S/SERPER01_Sergio_Perez/serper01.png`,
  alonso:         `${BASE}/F/FERALO01_Fernando_Alonso/feralo01.png`,
  bottas:         `${BASE}/V/VALBOT01_Valtteri_Bottas/valbot01.png`,
  hulkenberg:     `${BASE}/N/NICHUL01_Nico_Hulkenberg/nichul01.png`,
  stroll:         `${BASE}/L/LANSTR01_Lance_Stroll/lanstr01.png`,
};

export function getDriverImage(id) {
  return DRIVER_IMAGES[id] ?? null;
}
