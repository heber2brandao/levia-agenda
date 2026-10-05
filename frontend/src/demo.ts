export type Service = {
  id: string;
  name: string;
  price: number;
  duration: number;
  returnDays: number;
  active: boolean;
};
export const initialServices: Service[] = [
  {
    id: "1",
    name: "Manicure",
    price: 35,
    duration: 45,
    returnDays: 14,
    active: true,
  },
  {
    id: "2",
    name: "Pedicure",
    price: 45,
    duration: 60,
    returnDays: 21,
    active: true,
  },
  {
    id: "3",
    name: "Esmaltação em gel",
    price: 85,
    duration: 90,
    returnDays: 21,
    active: true,
  },
];
export const money = (value: number) =>
  value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export const appointments = [
  {
    time: "09:00",
    name: "Marina Alves",
    service: "Manicure",
    status: "Confirmado",
  },
  {
    time: "10:00",
    name: "Clara Santos",
    service: "Esmaltação em gel",
    status: "A confirmar",
  },
  {
    time: "13:30",
    name: "Beatriz Lima",
    service: "Pedicure",
    status: "Confirmado",
  },
];
