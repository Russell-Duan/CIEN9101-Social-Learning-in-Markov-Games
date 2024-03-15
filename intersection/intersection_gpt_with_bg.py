import os
import json
import openai
from dotenv import load_dotenv
from collections import defaultdict
import pandas as pd


class Car:
    def __init__(self, X: int, Y: int, color: str):
        self.X = X
        self.Y = Y
        self.color = color
        self.reward = 0
        self.playing = True
        self.XUpdate = X
        self.YUpdate = Y
        self.MoveUpdate = "Go"

    def set_reward_from_crash(self):
        self.reward -= 5

    def set_reward_from_move(self):
        self.reward -= 2

    def queue_update(self, X, Y, Move):
        self.XUpdate = X
        self.YUpdate = Y
        self.MoveUpdate = Move

    def update_position(self):
        self.X = self.XUpdate
        self.Y = self.YUpdate


class DrivingGame:
    def __init__(self, _system_prompt_str: str, _otherCar_prompt_str: str, _myCar_prompt_str: str):
        self.car_list = [Car(1, 5, "green"), Car(5, 1, "red"), Car(5, 2, "white")]
        # Prompt templates
        self._system_prompt_str = _system_prompt_str
        self._otherCar_prompt_str = _otherCar_prompt_str
        self._myCar_prompt_str = _myCar_prompt_str
        # Number of cars at given coordinates; convenient for checking crash
        self.position_count = defaultdict(int)
        self.output = list()

    def play(self):
        time_step = 1
        while True:
            # status at the beginning of the time step
            # print(f"Time Step {time_step}:")
            self.output.append({"Time_stamp": time_step})
            for my_car in self.car_list:
                if my_car.playing:
                    # print(f"{my_car.color} car: ({my_car.X}, {my_car.Y}), {my_car.reward}")
                    self.output[time_step - 1][str(my_car.color + "_car_x")] = my_car.X
                    self.output[time_step - 1][str(my_car.color + "_car_y")] = my_car.Y
                    self.output[time_step - 1][str(my_car.color + "_car_reward")] = my_car.reward
                    # exit game if needed
                    my_car.playing = (my_car.X != 9) if my_car.color == "green" else (my_car.Y != 9)
            # print('\n')

            # check game end
            if self.check_any_car_crash():
                print('Car crash. Game over.')
                return self.output, 0
            if self.check_all_car_not_playing():
                print(f"Both green and red cars reached the end of the road. Game over.")
                return self.output, 1
            if time_step > 25:
                break

            # Get (and queue) move update
            for my_car in self.car_list:
                if my_car.playing:
                    if my_car.color != "white":
                        Move, X_pos, Y_pos = self.get_openai_response(my_car)
                    else:
                        Move = "Go"
                        X_pos = my_car.X
                        Y_pos = my_car.Y + 1
                    my_car.queue_update(X_pos, Y_pos, Move)
                    self.output[time_step - 1][str(my_car.color + "_car_decision")] = Move
                    # print(f"{my_car.color} car chose {Move}")
                else:
                    print(f"{my_car.color} car has exited")

            # Update position and position_count
            self.position_count = defaultdict(int)
            for my_car in self.car_list:
                if my_car.playing:
                    my_car.update_position()
                    self.position_count[(my_car.X, my_car.Y)] += 1

            # Update reward
            for my_car in self.car_list:
                if my_car.playing:
                    my_car.set_reward_from_move()
                    if self.check_crash(my_car):
                        my_car.set_reward_from_crash()

            # print('\n')

            # increment time
            time_step += 1

    def check_all_car_not_playing(self):
        for my_car in self.car_list:
            if my_car.playing:
                return False
        return True

    def check_any_car_crash(self):
        for car in self.car_list:
            if car.playing and self.check_crash(car):
                return True
        return False

    def check_crash(self, car):
        return self.position_count[(car.X, car.Y)] > 1

    # get ai repsonse without changing anything variables yet
    def get_openai_response(self, my_car: Car) -> tuple[str, int, int]:
        # call as green or red
        # All the other_cars in the list
        other_car_list = list()
        for car in self.car_list:
            if my_car != car:
                other_car_list.append(car)

        # chatgpt prompt
        prompt = []

        # system prompt
        system_prompt = {
            'role': 'system',
            'content': self._system_prompt_str
        }
        prompt.append(system_prompt)

        # user prompt
        user_prompt = ""

        for other_car in other_car_list:
            other_position = f"({other_car.X},{other_car.Y})" if other_car.playing else \
                "somewhere outside this grid, no longer relevant"
            user_prompt += self._otherCar_prompt_str.replace('{otherColor}', other_car.color) \
                .replace('{otherPosition}', other_position)

        my_position = f"({my_car.X},{my_car.Y})"
        user_prompt += self._myCar_prompt_str.replace('{myColor}', my_car.color) \
            .replace('{myPosition}', my_position) \
            .replace('{myReward}', str(my_car.reward))

        user_prompt = {
            'role': 'user',
            'content': user_prompt
        }
        prompt.append(user_prompt)

        # Get AI response
        response = openai.chat.completions.create(
            model='gpt-4',
            messages=prompt,
            temperature=0,
            max_tokens=10,
            top_p=1,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        rspns_text = response.choices[0].message.content

        # analyze response
        rspns_list = rspns_text.strip('()').split(',')
        Move = rspns_list[0]
        X_pos = int(rspns_list[1])
        Y_pos = int(rspns_list[2])
        return Move, X_pos, Y_pos

def simulation(output_name: str, num_of_simulation: int, game: DrivingGame):

    df = list()

    # load config
    with open('.config') as f:    config = json.load(f)
    _system_prompt_str = config['system']
    _otherCar_prompt_str = config['otherCar']
    _myCar_prompt_str = config['myCar']

    counter = 0
    for i in range(num_of_simulation):
        game = DrivingGame(_system_prompt_str, _otherCar_prompt_str, _myCar_prompt_str)
        new_rows, success = game.play()
        print(new_rows)
        print('hi')
        counter += success
        print(success)
        for row in new_rows:
            row['Simulation'] = i+1

        new_df = pd.DataFrame(new_rows)
        if len(df) == 0:
            df = new_df
        else:
            df = pd.concat([df, new_df], ignore_index=True)

        print(i+1, "-th simulation complete")

    df.to_csv(output_name + '.csv', index=False)


if __name__ == "__main__":
    # load openai key
    load_dotenv()

    openai.api_key = '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'

    # load config
    with open('.config') as f:    config = json.load(f)
    _system_prompt_str = config['system']
    _otherCar_prompt_str = config['otherCar']
    _myCar_prompt_str = config['myCar']

    game = DrivingGame(_system_prompt_str, _otherCar_prompt_str, _myCar_prompt_str)
    simulation("output_with_bg", 2, game)